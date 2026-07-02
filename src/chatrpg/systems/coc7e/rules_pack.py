from __future__ import annotations

from chatrpg.ir.ruleset import ProcedureSpec, ResourceChangeSpec, RollSpec, RulesetIR


def build_coc7e_native_ruleset() -> RulesetIR:
    return RulesetIR(
        system_id="coc7e",
        edition="7e",
        character_schema={
            "resources": ["hp", "mp", "sanity", "luck"],
            "traits": ["str", "con", "siz", "dex", "app", "int", "pow", "edu"],
            "skills": "percentile",
        },
        resolution_kernels=[
            {"id": "coc7e.percentile_roll_under", "dice": "d100"},
            {"id": "coc7e.bonus_penalty_dice", "dice": "d100_with_tens_selection"},
            {"id": "coc7e.damage_roll", "dice": "damage_expression"},
            {"id": "coc7e.chase_movement", "dice": "d100"},
            {"id": "coc7e.madness_table", "dice": "d10"},
        ],
        procedures=[
            ProcedureSpec(
                id="coc7e.skill_roll",
                system_id="coc7e",
                name="Skill Roll",
                inputs=["actor_id", "skill_id", "trait_id", "target", "bonus_dice", "penalty_dice"],
                rolls=[RollSpec(id="roll", kernel_id="coc7e.percentile_roll_under")],
                events=["SkillRollResolved"],
            ),
            ProcedureSpec(
                id="coc7e.pushed_roll",
                system_id="coc7e",
                name="Pushed Roll",
                inputs=["actor_id", "skill_id", "trait_id", "target", "stakes"],
                rolls=[RollSpec(id="roll", kernel_id="coc7e.percentile_roll_under")],
                events=["PushedRollResolved"],
            ),
            ProcedureSpec(
                id="coc7e.luck_spend",
                system_id="coc7e",
                name="Luck Spend",
                inputs=["actor_id", "roll", "current_luck"],
                resource_changes=[
                    ResourceChangeSpec(resource_id="luck", expression="-luck_spent", timing="commit")
                ],
                events=["LuckSpent"],
            ),
            ProcedureSpec(
                id="coc7e.sanity_roll",
                system_id="coc7e",
                name="Sanity Roll",
                inputs=["actor_id", "success_loss", "failure_loss"],
                rolls=[RollSpec(id="sanity_roll", kernel_id="coc7e.percentile_roll_under")],
                resource_changes=[
                    ResourceChangeSpec(resource_id="sanity", expression="-sanity_lost", timing="commit")
                ],
                events=["SanityRollResolved", "CharacterResourceChanged", "CharacterConditionAdded"],
            ),
            ProcedureSpec(
                id="coc7e.opposed_roll",
                system_id="coc7e",
                name="Opposed Roll",
                inputs=["attacker_id", "defender_id", "attacker_target", "defender_target"],
                rolls=[
                    RollSpec(id="attacker_roll", kernel_id="coc7e.percentile_roll_under"),
                    RollSpec(id="defender_roll", kernel_id="coc7e.percentile_roll_under"),
                ],
                events=["OpposedRollResolved"],
            ),
            ProcedureSpec(
                id="coc7e.combat_attack",
                system_id="coc7e",
                name="Combat Attack",
                inputs=["actor_id", "skill_id", "target", "damage", "range_type"],
                rolls=[
                    RollSpec(id="attack_roll", kernel_id="coc7e.percentile_roll_under"),
                    RollSpec(id="damage", kernel_id="coc7e.damage_roll"),
                ],
                resource_changes=[
                    ResourceChangeSpec(resource_id="hp", expression="-total_damage", timing="commit")
                ],
                events=["AttackResolved", "CharacterResourceChanged", "CharacterConditionAdded"],
            ),
            ProcedureSpec(
                id="coc7e.chase_round",
                system_id="coc7e",
                name="Chase Round",
                inputs=["participants", "movement_actor_id", "skill_id", "target"],
                rolls=[RollSpec(id="movement_check", kernel_id="coc7e.chase_movement")],
                events=["ChaseRoundResolved"],
            ),
            ProcedureSpec(
                id="coc7e.first_aid",
                system_id="coc7e",
                name="First Aid",
                inputs=["actor_id", "target_actor_id", "skill_id", "healing"],
                rolls=[RollSpec(id="first_aid_roll", kernel_id="coc7e.percentile_roll_under")],
                resource_changes=[ResourceChangeSpec(resource_id="hp", expression="+healing", timing="commit")],
                events=["FirstAidResolved", "CharacterResourceChanged", "CharacterConditionRemoved"],
            ),
            ProcedureSpec(
                id="coc7e.medicine",
                system_id="coc7e",
                name="Medicine",
                inputs=["actor_id", "target_actor_id", "skill_id", "healing"],
                rolls=[RollSpec(id="medicine_roll", kernel_id="coc7e.percentile_roll_under")],
                resource_changes=[ResourceChangeSpec(resource_id="hp", expression="+healing", timing="commit")],
                events=["MedicineResolved", "CharacterResourceChanged", "CharacterConditionRemoved"],
            ),
            ProcedureSpec(
                id="coc7e.bout_of_madness",
                system_id="coc7e",
                name="Bout of Madness",
                inputs=["actor_id", "mode"],
                rolls=[RollSpec(id="madness_table_roll", kernel_id="coc7e.madness_table")],
                events=["BoutOfMadnessResolved", "CharacterConditionAdded"],
            ),
            ProcedureSpec(
                id="coc7e.cast_spell",
                system_id="coc7e",
                name="Cast Spell",
                inputs=["actor_id", "mp_cost", "sanity_cost", "power_roll_target"],
                rolls=[RollSpec(id="optional_power_roll", kernel_id="coc7e.percentile_roll_under")],
                resource_changes=[
                    ResourceChangeSpec(resource_id="mp", expression="-mp_spent", timing="commit"),
                    ResourceChangeSpec(resource_id="sanity", expression="-sanity_spent", timing="commit"),
                ],
                events=["SpellCastResolved", "CharacterResourceChanged"],
            ),
            ProcedureSpec(
                id="coc7e.study_tome",
                system_id="coc7e",
                name="Study Mythos Tome",
                inputs=["actor_id", "title", "weeks_required", "mythos_gain", "sanity_loss"],
                rolls=[RollSpec(id="tome_sanity_loss", kernel_id="coc7e.damage_roll")],
                resource_changes=[
                    ResourceChangeSpec(resource_id="sanity", expression="-sanity_loss", timing="commit")
                ],
                events=["TomeStudyResolved", "CharacterSkillChanged", "CharacterResourceChanged"],
            ),
            ProcedureSpec(
                id="coc7e.investigator_development",
                system_id="coc7e",
                name="Investigator Development",
                inputs=["actor_id", "skill_id", "current_value"],
                rolls=[
                    RollSpec(id="improvement_check", kernel_id="coc7e.percentile_roll_under"),
                    RollSpec(id="improvement_gain", kernel_id="coc7e.damage_roll"),
                ],
                events=["SkillImprovementResolved", "CharacterSkillChanged"],
            ),
        ],
    )
