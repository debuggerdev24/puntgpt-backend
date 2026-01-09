from django.core.management.base import BaseCommand
from horse_race.models.race import Race
from horse_race.models.meeting import Meeting
from horse_race.models.selection import Selection
from datetime import date
import requests
from django.utils.dateparse import parse_datetime

class Command(BaseCommand):
    help = 'Fetch odds and PlayUp IDs from PlayUp API and save to local DB'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting PlayUp data sync...'))
        
        # 1. Fetch Meetings
        # Corrected parameter name from pag[size] to page[size]
        base_url = "https://wagering-api.playup.io/v1/meetings/?include=races&page[size]=100"
        
        response = requests.get(base_url)
        if response.status_code != 200:
            self.stdout.write(self.style.ERROR(f"Failed to fetch meetings: {response.status_code}"))
            return

        data = response.json()
        meetings_data = data.get('data', [])
        
        # Iterate through meetings
        for m_node in meetings_data:
            attrs = m_node.get('attributes', {})
            m_id = m_node.get('id')
            start_date_str = attrs.get('start_date')
            start_time_str = attrs.get('start_time')
            track_name = attrs.get('track', {}).get('name')
            
            # Check date (Today only)
            if start_date_str != str(date.today()):
                continue

            # Find matching Meeting in DB
            # Matching by Date and Track Name. 
            meeting_qs = Meeting.objects.filter(
                date=start_date_str, startTimeUtc=start_time_str,
                track__name__iexact=track_name
            )
            meeting_obj = meeting_qs.first()

            if not meeting_obj:
                self.stdout.write(self.style.WARNING(f"Skipping meeting (not found in DB): {track_name} on {start_date_str}"))
                continue

            # Update Meeting PlayUp ID
            if meeting_obj.playup_meeting_id != m_id:
                meeting_obj.playup_meeting_id = m_id
                meeting_obj.save()
                self.stdout.write(f"Updated Meeting: {meeting_obj} (PlayUp ID: {m_id})")

            # Process Races in this Meeting
            # We get race IDs from relationships to fetch details
            self.stdout.write(f"Processing Races for Meeting: {meeting_obj}")
            races_data = m_node.get('relationships', {}).get('races', {}).get('data', [])
            
            for r_rel in races_data:
                playup_race_id = r_rel.get('id')
                self.stdout.write(f"Processing Race: {playup_race_id}")
                self.process_race(playup_race_id, meeting_obj)

    def process_race(self, playup_race_id, meeting_obj):
        # Fetch race details
        url = f"https://wagering-api.playup.io/v1/races/{playup_race_id}/?include=meeting,available_bet_types,selections.prices"
        try:
            resp = requests.get(url, timeout=10)
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"Error fetching race {playup_race_id}: {e}"))
            return

        if resp.status_code != 200:
            return

        r_data = resp.json()
        main_data = r_data.get('data', {})
        included = r_data.get('included', [])
        
        attrs = main_data.get('attributes', {})
        # race_num = attrs.get('race_number')
        race_name = attrs.get('name')
        race_start_time = attrs.get('start_time')

        # Find matching Race in DB
        self.stdout.write((f"Going for the filtering for race: {playup_race_id}"))
        race_qs = Race.objects.filter(meeting=meeting_obj, startTimeUtc=race_start_time)
        self.stdout.write((f"Got the filtering for race: {playup_race_id}---{race_qs}"))
        race_obj = race_qs.first()
        self.stdout.write((f"Returned result: {race_obj.raceId}"))

        if not race_obj:
            self.stdout.write(self.style.WARNING(f"  Race not found in DB for meeting {meeting_obj}"))
            return

        # Update Race PlayUp ID (Forced for verification)
        race_obj.playup_race_id = playup_race_id
        race_obj.save()
        self.stdout.write(self.style.SUCCESS(f"  Race table updated with PlayUp ID: {playup_race_id}"))

        # Process Selections
        # Build lookups
        included_selections = {x['id']: x for x in included if x['type'] == 'selections'}
        included_prices = {x['id']: x for x in included if x['type'] == 'prices'}

        selections_rels = main_data.get('relationships', {}).get('selections', {}).get('data', [])

        for s_rel in selections_rels:
            p_sel_id = s_rel.get('id')
            p_sel_data = included_selections.get(p_sel_id)
            
            if not p_sel_data:
                continue

            s_attrs = p_sel_data.get('attributes', {})
            horse_name = s_attrs.get('name')
            jockey_name = s_attrs.get('jockey')
            trainer_name = s_attrs.get('trainer')
            
            # Find matching Selection in DB
            # 1. Try matching by Number (Most reliable)
            sel_number = s_attrs.get('number')
            sel_obj = None
            
            if sel_number is not None:
                sel_obj = Selection.objects.filter(
                    race=race_obj,
                    number=sel_number
                ).first()

            # 2. Fallback: Match by Horse Name AND Jockey (if number match failed)
            # useful if scratchings caused number shifts, though unlikely in short term
            if not sel_obj and horse_name:
                sel_obj = Selection.objects.filter(
                    race=race_obj,
                    horse__name__icontains=horse_name
                ).first()
            
            if not sel_obj:
                self.stdout.write(self.style.WARNING(f"    Selection NOT found: #{sel_number} {horse_name}"))
                continue

            self.stdout.write(f"    Syncing Selection: #{sel_obj.number} {sel_obj.horse.name}")

            # Update Selection content
            updated = False
            if sel_obj.playup_selection_id != p_sel_id:
                sel_obj.playup_selection_id = p_sel_id
                updated = True

            # Fluctuations
            flucs = s_attrs.get('display_price_flucs')
            if flucs is not None:
                sel_obj.playup_price_fluctuations = flucs
                updated = True

            # Prices
            # Extract Fixed Win and Place
            prices_rels = p_sel_data.get('relationships', {}).get('prices', {}).get('data', [])
            
            win_price = None
            place_price = None

            for pr_rel in prices_rels:
                pr_id = pr_rel.get('id')
                pr_node = included_prices.get(pr_id)
                if not pr_node:
                    continue
                
                pr_attrs = pr_node.get('attributes', {})
                prod_name = pr_attrs.get('product', {}).get('name')
                bet_name = pr_attrs.get('bet_type', {}).get('name')
                d_price = pr_attrs.get('d_price')
                
                if prod_name == "Fixed Price":
                    if bet_name == "Win":
                        win_price = d_price
                    elif bet_name == "Place":
                        place_price = d_price

            if win_price is not None:
                sel_obj.playup_fixed_odds_win = win_price
                updated = True
            
            if place_price is not None:
                sel_obj.playup_fixed_odds_place = place_price
                updated = True

            if updated:
                sel_obj.save()
