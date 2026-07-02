"""seed The Haunting AdventureIR

Revision ID: 0003_seed_the_haunting_adventure
Revises: 0002_parser_runtime_debug
Create Date: 2026-07-02
"""
from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa

revision = "0003_seed_the_haunting_adventure"
down_revision = "0002_parser_runtime_debug"
branch_labels = None
depends_on = None

ADVENTURE_ID = "the_haunting"
SYSTEM_ID = "coc7e"
DOCUMENT_ID = "coc7e_keeper"


def ref(page: int) -> dict[str, object]:
    return {"document_id": DOCUMENT_ID, "page_start": page, "page_end": page, "visibility": "keeper"}


def unit(unit_id: str, kind: str, title: str, summary: str, page: int, visibility: str = "keeper_only", parent_id: str | None = None) -> dict[str, object]:
    return {"id": unit_id, "adventure_id": ADVENTURE_ID, "kind": kind, "title": title, "summary": summary, "visibility": visibility, "parent_id": parent_id, "facets": [], "source_refs": [ref(page)]}


def revelation(revelation_id: str, truth: str, page: int, unlocks: list[str] | None = None) -> dict[str, object]:
    return {"id": revelation_id, "adventure_id": ADVENTURE_ID, "truth_summary": truth, "required_for": [], "unlocks": unlocks or [], "redundancy_level": 1, "source_refs": [ref(page)]}


def clue(clue_id: str, revelation_id: str, carrier_type: str, unit_id: str, acquisition: str, page: int, skills: list[str] | None = None, fail_forward: str | None = None, visibility: str = "keeper_only") -> dict[str, object]:
    return {"id": clue_id, "revelation_id": revelation_id, "carrier_type": carrier_type, "unit_id": unit_id, "acquisition": acquisition, "suggested_skills": skills or [], "fail_forward": fail_forward, "visibility": visibility, "source_refs": [ref(page)]}


def handout(handout_id: str, title: str, summary: str, reveals: list[str], page: int) -> dict[str, object]:
    return {"id": handout_id, "adventure_id": ADVENTURE_ID, "title": title, "summary": summary, "asset_ref": None, "reveals": reveals, "source_refs": [ref(page)]}


def build_adventure_ir() -> dict[str, object]:
    units = [
        unit("unit_setup", "briefing", "The Job from Mr. Knott", "The investigators are hired in 1920s Boston to look into the troubled Corbitt House before the landlord can safely rent or sell it.", 435, "player_visible"),
        unit("unit_boston_globe", "research_location", "Boston Globe", "Newspaper research can uncover the house's history of accidents, deaths, illnesses, madness, and the Macario family's recent tragedy.", 436),
        unit("unit_central_library", "research_location", "Central Library", "Library research reveals Walter Corbitt's acquisition of the house, lawsuits concerning his conduct, and the unresolved burial dispute.", 438),
        unit("unit_hall_records", "research_location", "Hall of Records", "Civil and church records connect Corbitt's will to Rev. Michael Thomas and the Chapel of Contemplation.", 438),
        unit("unit_police_records", "research_location", "Higher Courts and Central Police Station", "Access to higher court or police records reveals the Chapel of Contemplation raid, arrests, deaths, and suspected cover-up.", 438),
        unit("unit_neighborhood", "social_location", "The Neighborhood", "The Corbitt House is the last private residence on a business block; Mr. Dooley can gossip about the Macarios and point to the Chapel ruins.", 439),
        unit("unit_roxbury_sanitarium", "social_location", "Roxbury Sanitarium", "Vittorio and Gabriela Macario can provide disturbing testimony about the presence in the house and a hint about Corbitt's own weapon.", 439),
        unit("unit_chapel", "investigation_location", "Chapel of Contemplation Ruins", "The ruined chapel contains occult signs, hazards, old records, and Mythos material connecting Corbitt to buried secrets.", 439),
        unit("unit_corbitt_house", "investigation_location", "Old Corbitt Place", "The house appears abandoned and locked down; exploration moves from eerie domestic remains toward supernatural escalation.", 441),
        unit("unit_house_storage", "room", "Ground Floor Storage Room", "A boarded cupboard contains Corbitt diaries describing occult experiments and an advanced summoning spell.", 442, parent_id="unit_corbitt_house"),
        unit("unit_house_living", "room", "Living Room", "The room is crowded with Catholic devotional objects left by former occupants who feared the house.", 442, parent_id="unit_corbitt_house"),
        unit("unit_house_spare_bedroom", "room", "Spare Bedroom", "Corbitt can stage disturbances here and launch the dangerous bed attack.", 443, parent_id="unit_corbitt_house"),
        unit("unit_house_chapel_crawlspace", "room", "Hidden Crawl Space", "A rat pack and an obvious inscription connect the house interior to the Chapel of Contemplation.", 447, parent_id="unit_corbitt_house"),
        unit("unit_house_basement", "room", "Basement and Corbitt's Body", "The final confrontation centers on Corbitt's preserved corpse, his magic, and his floating dagger.", 447, parent_id="unit_corbitt_house"),
        unit("unit_conclusion", "outcome", "Conclusion", "Victory destroys Corbitt and rewards the investigators; failure can leave the landlord dead and the investigators under suspicion.", 448),
    ]
    revelations = [
        revelation("rev_house_is_haunted", "The Corbitt House is not merely unlucky; a malign presence actively attacks residents and intruders.", 435, ["unit_corbitt_house"]),
        revelation("rev_walter_corbitt", "Walter Corbitt is the central historical figure behind the house and its occult legacy.", 438),
        revelation("rev_corbitt_buried_in_house", "Corbitt arranged to be buried in the house basement, and that burial is key to the haunting.", 440, ["unit_house_basement"]),
        revelation("rev_chapel_connection", "Corbitt is tied to the Chapel of Contemplation and its occult leadership.", 438, ["unit_chapel"]),
        revelation("rev_chapel_raid_coverup", "The Chapel of Contemplation was violently raided in 1912, with deaths, arrests, and signs of official interference.", 438),
        revelation("rev_own_dagger", "Corbitt can be permanently defeated with his own dagger if the investigators seize and use it against him.", 439),
        revelation("rev_liber_ivonis", "The Chapel ruins contain a damaged Mythos tome that can increase Cthulhu Mythos knowledge at the cost of maximum Sanity.", 440),
        revelation("rev_corbitt_final_threat", "Corbitt is an undead sorcerer who can animate his body, cast spells, and use a floating dagger.", 447),
    ]
    clues = [
        clue("clue_knott_briefing", "rev_house_is_haunted", "briefing", "unit_setup", "automatic briefing", 435, visibility="player_visible"),
        clue("clue_globe_history", "rev_house_is_haunted", "newspaper research", "unit_boston_globe", "Persuade or related social access to newspaper morgue", 436, ["Persuade", "Charm", "Fast Talk"], "Players can later learn related history through library or neighborhood gossip."),
        clue("clue_library_corbitt_owner", "rev_walter_corbitt", "library handout", "unit_central_library", "Library Use research", 438, ["Library Use"], "Each half-day allows another attempt."),
        clue("clue_library_burial_lawsuit", "rev_corbitt_buried_in_house", "library handout", "unit_central_library", "Library Use research", 438, ["Library Use"], "The Hall of Records can also point toward the burial dispute."),
        clue("clue_records_executor", "rev_chapel_connection", "civil record", "unit_hall_records", "Library Use at Hall of Records", 438, ["Library Use", "Law"], "A courteous clerk or legal reasoning can redirect toward higher court records."),
        clue("clue_police_raid", "rev_chapel_raid_coverup", "police file", "unit_police_records", "Law, Credit Rating, Persuade, Charm, or Fast Talk", 438, ["Law", "Credit Rating", "Persuade", "Charm", "Fast Talk"], "A pushed roll can still obtain a contact, with possible social fallout."),
        clue("clue_dooley_gossip", "rev_house_is_haunted", "npc gossip", "unit_neighborhood", "APP, Credit Rating, Charm, Fast Talk, Persuade, or Intimidate", 439, ["Charm", "Fast Talk", "Persuade", "Intimidate", "Credit Rating"], "Dooley may exaggerate but can still point to the house and Chapel."),
        clue("clue_vittorio_quote", "rev_own_dagger", "npc clue", "unit_roxbury_sanitarium", "interview Vittorio Macario", 439, fail_forward="Gabriela's testimony still confirms the presence even if Vittorio is hard to interpret."),
        clue("clue_gabriela_presence", "rev_house_is_haunted", "npc testimony", "unit_roxbury_sanitarium", "interview Gabriela Macario", 439, fail_forward="Keep the interview brief to avoid upsetting her."),
        clue("clue_chapel_symbol", "rev_chapel_connection", "visual handout", "unit_chapel", "visit Chapel ruins", 440, fail_forward="The symbol can be shown as a handout and associated with the old cult site."),
        clue("clue_chapel_journal", "rev_corbitt_buried_in_house", "hidden journal", "unit_chapel", "Spot Hidden or careful search after chapel basement fall", 440, ["Spot Hidden"], "The fall itself can still reveal the sealed basement space."),
        clue("clue_chapel_tome", "rev_liber_ivonis", "mythos tome", "unit_chapel", "Spot Hidden or careful search after chapel basement fall", 440, ["Spot Hidden", "Read Latin"], "The tome can be identified later if no one can read it immediately."),
        clue("clue_diaries_occult", "rev_walter_corbitt", "diaries", "unit_house_storage", "open boarded cupboard and read diaries", 442, fail_forward="The diaries take significant time and carry Sanity/Mythos consequences."),
        clue("clue_crawlspace_words", "rev_chapel_connection", "obvious inscription", "unit_house_chapel_crawlspace", "enter crawl space", 447, fail_forward="This clue should not require Spot Hidden."),
        clue("clue_final_body", "rev_corbitt_final_threat", "final encounter", "unit_house_basement", "find Corbitt's body", 447, fail_forward="The rising corpse triggers SAN and combat procedures."),
    ]
    npcs = [
        {"id": "npc_mr_knott", "adventure_id": ADVENTURE_ID, "name": "Mr. Steven Knott", "summary": "Landlord and patron who hires the investigators to clear the Corbitt House's reputation.", "public_profile": "Anxious property owner willing to pay for investigation.", "keeper_profile": "He wants the house usable again and may become a victim if Corbitt is not stopped.", "stats_ref": None, "unit_ids": ["unit_setup", "unit_conclusion"], "source_refs": [ref(435), ref(448)]},
        {"id": "npc_walter_corbitt", "adventure_id": ADVENTURE_ID, "name": "Walter Corbitt", "summary": "Undead sorcerer and central antagonist whose preserved body haunts the house.", "public_profile": None, "keeper_profile": "Malicious, magically preserved, and capable of animating his body, using spells, and controlling a floating dagger.", "stats_ref": "entity_walter_corbitt", "unit_ids": ["unit_house_basement"], "source_refs": [ref(447), ref(449)]},
        {"id": "npc_mr_dooley", "adventure_id": ADVENTURE_ID, "name": "Mr. Dooley", "summary": "Neighborhood cigar and newspaper vendor who can provide gossip about the Macarios and the house.", "public_profile": "Talkative local vendor.", "keeper_profile": "May exaggerate, but he can point to useful local information.", "stats_ref": None, "unit_ids": ["unit_neighborhood"], "source_refs": [ref(439)]},
        {"id": "npc_vittorio_macario", "adventure_id": ADVENTURE_ID, "name": "Vittorio Macario", "summary": "Former tenant now confined at Roxbury Sanitarium after the house broke him.", "public_profile": "Mentally unwell former resident.", "keeper_profile": "His biblical-sounding phrase foreshadows the dagger solution.", "stats_ref": None, "unit_ids": ["unit_roxbury_sanitarium"], "source_refs": [ref(439)]},
        {"id": "npc_gabriela_macario", "adventure_id": ADVENTURE_ID, "name": "Gabriela Macario", "summary": "Former tenant who can describe the presence and its attacks within the house.", "public_profile": "Recovering witness at the sanitarium.", "keeper_profile": "She confirms the haunting but cannot identify Corbitt precisely.", "stats_ref": None, "unit_ids": ["unit_roxbury_sanitarium"], "source_refs": [ref(439)]},
        {"id": "npc_michael_thomas", "adventure_id": ADVENTURE_ID, "name": "Pastor Michael Thomas", "summary": "Pastor tied to the Chapel of Contemplation and Corbitt's will.", "public_profile": None, "keeper_profile": "Court and police records place him at the center of the cult's legal aftermath.", "stats_ref": None, "unit_ids": ["unit_hall_records", "unit_police_records"], "source_refs": [ref(438)]},
    ]
    locations = [
        {"id": "loc_boston", "adventure_id": ADVENTURE_ID, "name": "Boston, Massachusetts", "summary": "Default 1920 setting for the investigation.", "parent_location_id": None, "unit_ids": ["unit_setup"], "exits_to": ["loc_boston_globe", "loc_central_library", "loc_hall_records", "loc_corbitt_house"], "source_refs": [ref(435)]},
        {"id": "loc_boston_globe", "adventure_id": ADVENTURE_ID, "name": "Boston Globe", "summary": "Newspaper office whose clipping files can reveal earlier incidents at the house.", "parent_location_id": "loc_boston", "unit_ids": ["unit_boston_globe"], "exits_to": [], "source_refs": [ref(436)]},
        {"id": "loc_central_library", "adventure_id": ADVENTURE_ID, "name": "Central Library", "summary": "Research location providing chronological records about Corbitt and his lawsuits.", "parent_location_id": "loc_boston", "unit_ids": ["unit_central_library"], "exits_to": [], "source_refs": [ref(438)]},
        {"id": "loc_hall_records", "adventure_id": ADVENTURE_ID, "name": "Hall of Records", "summary": "Civil and church records link Corbitt to the Chapel of Contemplation.", "parent_location_id": "loc_boston", "unit_ids": ["unit_hall_records"], "exits_to": ["loc_police_station"], "source_refs": [ref(438)]},
        {"id": "loc_police_station", "adventure_id": ADVENTURE_ID, "name": "Higher Courts and Central Police Station", "summary": "Restricted records concerning the Chapel raid can be obtained with successful social or legal access.", "parent_location_id": "loc_boston", "unit_ids": ["unit_police_records"], "exits_to": [], "source_refs": [ref(438)]},
        {"id": "loc_roxbury_sanitarium", "adventure_id": ADVENTURE_ID, "name": "Roxbury Sanitarium", "summary": "Where Vittorio and Gabriela Macario can be interviewed.", "parent_location_id": "loc_boston", "unit_ids": ["unit_roxbury_sanitarium"], "exits_to": [], "source_refs": [ref(439)]},
        {"id": "loc_chapel", "adventure_id": ADVENTURE_ID, "name": "Chapel of Contemplation Ruins", "summary": "Ruined occult site a few blocks from the house.", "parent_location_id": "loc_boston", "unit_ids": ["unit_chapel"], "exits_to": [], "source_refs": [ref(439), ref(440)]},
        {"id": "loc_corbitt_house", "adventure_id": ADVENTURE_ID, "name": "Old Corbitt Place", "summary": "The haunted house where the final confrontation occurs.", "parent_location_id": "loc_boston", "unit_ids": ["unit_corbitt_house", "unit_house_storage", "unit_house_living", "unit_house_spare_bedroom", "unit_house_chapel_crawlspace", "unit_house_basement"], "exits_to": [], "source_refs": [ref(441), ref(442), ref(443), ref(447)]},
    ]
    encounters = [
        {"id": "enc_chapel_floor_collapse", "adventure_id": ADVENTURE_ID, "name": "Chapel Floor Collapse", "summary": "Unsafe chapel flooring can drop investigators into a sealed basement space; use Luck and Jump, with 1D6 damage on a fall.", "procedure_ids": ["coc7e.skill_roll"], "unit_ids": ["unit_chapel"], "source_refs": [ref(440)]},
        {"id": "enc_bed_attack", "adventure_id": ADVENTURE_ID, "name": "Spare Bedroom Bed Attack", "summary": "Corbitt may hurl the bed at an investigator by the window; use Spot Hidden, Dodge, damage, and SAN 1/1D4 for witnesses.", "procedure_ids": ["coc7e.skill_roll", "coc7e.sanity_roll", "coc7e.combat_attack"], "unit_ids": ["unit_house_spare_bedroom"], "source_refs": [ref(443)]},
        {"id": "enc_rat_pack", "adventure_id": ADVENTURE_ID, "name": "Rat Pack", "summary": "A rat pack can attack or overwhelm investigators near the crawl space.", "procedure_ids": ["coc7e.combat_attack"], "unit_ids": ["unit_house_chapel_crawlspace"], "source_refs": [ref(447)]},
        {"id": "enc_corbitt_final", "adventure_id": ADVENTURE_ID, "name": "Walter Corbitt Final Confrontation", "summary": "Corbitt rises, triggers SAN 1/1D8, uses Dominate, Flesh Ward, claw attacks, and a floating dagger. Seizing his own dagger can end him decisively.", "procedure_ids": ["coc7e.sanity_roll", "coc7e.combat_attack", "coc7e.cast_spell"], "unit_ids": ["unit_house_basement"], "source_refs": [ref(447), ref(448), ref(449)]},
    ]
    handouts = [
        handout("handout_1_job", "Mr. Knott's Assignment", "The investigators are asked to examine the Corbitt House and are directed toward research before entering the house.", ["rev_house_is_haunted"], 435),
        handout("handout_2_globe", "Boston Globe Unpublished Story", "A newspaper file summarizes prior tragedies and illnesses connected with the house.", ["rev_house_is_haunted"], 450),
        handout("handout_3_1835", "1835 House Record", "A merchant built the house, became ill, and sold it to Walter Corbitt.", ["rev_walter_corbitt"], 438),
        handout("handout_4_1852", "1852 Lawsuit", "Neighbors sued Corbitt over suspicious habits and demeanor.", ["rev_walter_corbitt"], 438),
        handout("handout_5_obituary", "Corbitt Obituary and Burial Dispute", "Corbitt's obituary and burial dispute point toward his continued link to the property.", ["rev_corbitt_buried_in_house"], 438),
        handout("handout_6_no_outcome", "Missing Lawsuit Outcome", "No recorded outcome is found for the second lawsuit over Corbitt's burial.", ["rev_corbitt_buried_in_house"], 438),
        handout("handout_7_church_records", "Church and Will Records", "Civil and church records identify Rev. Michael Thomas and the Chapel of Contemplation.", ["rev_chapel_connection"], 438),
        handout("handout_8_police_file", "Chapel Raid Police File", "The police file describes the raid, deaths, arrests, and signs of a suppressed scandal.", ["rev_chapel_raid_coverup"], 438),
        handout("handout_9_chapel_symbol", "Chapel Symbol", "A symbol of three Y shapes around a staring eye is found freshly painted at the Chapel ruins.", ["rev_chapel_connection"], 440),
    ]
    timelines = [
        {"id": "time_1835", "adventure_id": ADVENTURE_ID, "label": "1835", "summary": "The house is built and soon sold to Walter Corbitt after the builder falls ill.", "unlocks": ["rev_walter_corbitt"], "source_refs": [ref(438)]},
        {"id": "time_1852", "adventure_id": ADVENTURE_ID, "label": "1852", "summary": "Neighbors sue Corbitt over alarming conduct.", "unlocks": ["rev_walter_corbitt"], "source_refs": [ref(438)]},
        {"id": "time_1866", "adventure_id": ADVENTURE_ID, "label": "1866", "summary": "Corbitt's obituary and burial dispute keep attention on the house basement.", "unlocks": ["rev_corbitt_buried_in_house"], "source_refs": [ref(438)]},
        {"id": "time_1912", "adventure_id": ADVENTURE_ID, "label": "1912", "summary": "The Chapel of Contemplation is raided, leaving dead cultists and police officers plus signs of a cover-up.", "unlocks": ["rev_chapel_raid_coverup"], "source_refs": [ref(438)]},
        {"id": "time_1918", "adventure_id": ADVENTURE_ID, "label": "1918", "summary": "The Macario family occupies the house and suffers the tragedy that prompts Knott's investigation.", "unlocks": ["rev_house_is_haunted"], "source_refs": [ref(436), ref(439)]},
        {"id": "time_1920", "adventure_id": ADVENTURE_ID, "label": "1920", "summary": "The investigators are hired to solve the house's reputation and danger.", "unlocks": ["unit_setup"], "source_refs": [ref(435)]},
    ]
    return {"adventure_id": ADVENTURE_ID, "system_id": SYSTEM_ID, "title": "The Haunting", "units": units, "revelations": revelations, "clues": clues, "npcs": npcs, "locations": locations, "encounters": encounters, "handouts": handouts, "timelines": timelines, "source_refs": [{"document_id": DOCUMENT_ID, "page_start": 435, "page_end": 449, "visibility": "keeper"}]}


def upgrade() -> None:
    adventure = build_adventure_ir()
    op.get_bind().execute(
        sa.text("""
            insert into adventures (id, system_id, title, ir, source_refs)
            values (:id, :system_id, :title, cast(:ir as jsonb), cast(:source_refs as jsonb))
            on conflict (id) do update set
              system_id = excluded.system_id,
              title = excluded.title,
              ir = excluded.ir,
              source_refs = excluded.source_refs
        """),
        {"id": ADVENTURE_ID, "system_id": SYSTEM_ID, "title": adventure["title"], "ir": json.dumps(adventure), "source_refs": json.dumps(adventure["source_refs"])},
    )


def downgrade() -> None:
    op.execute(sa.text("delete from adventures where id = :id").bindparams(id=ADVENTURE_ID))
