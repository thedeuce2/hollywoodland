import pytest
from hollywoodland.systems.engine import HollywoodlandEngine
from hollywoodland.models.entities import CORE_ATTRIBUTES


def test_database_and_engine_initialization():
    engine = HollywoodlandEngine(seed=42)
    assert len(engine.db.db1) == 79
    assert len(engine.db.db2) == 42
    assert len(engine.db.events) == 278
    assert len(engine.actors) == 280
    assert len(engine.agencies) >= 35
    assert len(engine.films) == 54
    movie_budgets = [f.budget for f in engine.films.values() if f.series_or_movie == "Movie"]
    assert len(movie_budgets) == 36
    assert len(set(movie_budgets)) >= 15
    assert min(movie_budgets) < 5_000_000
    assert max(movie_budgets) >= 100_000_000
    assert engine.player_agency.name == "Hollywoodland Talent"
    assert engine.player_agency.budget == 50000.0


def test_signing_scouting_and_casting_workflow():
    engine = HollywoodlandEngine(seed=101)
    # 1. Pick a free agent
    free_agents = [a for a in engine.actors.values() if a.agency_id is None and a.fame_tier == "Unknown"]
    assert len(free_agents) > 0
    actor = free_agents[0]

    # 2. Scout actor
    ok, msg = engine.hire_scout(actor.id, 1)
    assert ok, msg
    assert engine.player_agency.budget == 50000.0 - 300

    # 3. Sign actor to player agency
    demands = engine.get_actor_initial_demands(actor.id)
    demands.signature_fee = 0
    ok, msg, _ = engine.sign_actor_to_player_agency(actor.id, demands)
    assert ok, msg
    assert actor.agency_id == 0
    assert all(actor.known_attributes[k] for k in CORE_ATTRIBUTES)

    # 4. Find an eligible matching role and submit actor
    actor.personal_info = []  # ensure no genre phobia blocks test submission
    matches = engine.find_matching_roles_for_actor(actor.id, include_ineligible=False)
    assert len(matches) > 0
    film, role = matches[0]["film"], matches[0]["role"]
    ok, msg = engine.submit_actor_to_role(actor.id, film.id, role.index)
    assert ok, msg
    assert actor.id in role.submitted_actor_ids

    # 5. Advance 60 days and auto-handle any blocking role contract offers
    for _ in range(60):
        blocker = engine.has_blocking_message()
        if blocker:
            for b in blocker.buttons:
                if b.command.startswith("ROLE_OFFER:"):
                    _, fid_s, ridx_s, aid_s = b.command.split(":")
                    offer = engine.get_initial_role_offer(int(fid_s), int(ridx_s), int(aid_s))
                    engine.finalize_role_contract(int(fid_s), int(ridx_s), int(aid_s), offer)
            blocker.requires_response = False
        ok, _ = engine.advance_day()
        assert ok


def test_role_finder_matching_and_sorting():
    engine = HollywoodlandEngine(seed=77)
    actor = next(a for a in engine.actors.values() if a.agency_id is None)
    eligible_matches = engine.find_matching_roles_for_actor(actor.id, include_ineligible=False)
    all_matches = engine.find_matching_roles_for_actor(actor.id, include_ineligible=True)

    assert len(all_matches) >= len(eligible_matches)
    assert len(eligible_matches) > 0
    assert all(m["eligible"] for m in eligible_matches)
    # Verify descending match_pct order among eligible roles
    pcts = [m["match_pct"] for m in eligible_matches]
    assert pcts == sorted(pcts, reverse=True)
    assert all(1 <= p <= 99 for p in pcts)
    # Verify eligible roles sort before ineligible roles when include_ineligible=True
    seen_ineligible = False
    for m in all_matches:
        if not m["eligible"]:
            seen_ineligible = True
        else:
            assert not seen_ineligible


def test_external_roster_pack_loading(tmp_path):
    import json
    pack_dir = tmp_path / "test_real_world"
    pack_dir.mkdir()
    (pack_dir / "manifest.json").write_text(json.dumps({"name": "Test Real World Pack", "version": "1.0"}), encoding="utf-8")
    (pack_dir / "actors.json").write_text(json.dumps([
        {"name": "Cillian Murphy", "sex": "Male", "age": 49, "nationality": "Ireland", "tmdb_popularity": 68.0, "tmdb_avg_vote": 7.8, "tmdb_credit_count": 48, "top_genres": ["Drama", "Crime/Thriller"]},
        {"name": "Emma Stone", "sex": "Female", "age": 37, "nationality": "USA", "tmdb_popularity": 64.0, "tmdb_avg_vote": 7.6, "tmdb_credit_count": 42, "top_genres": ["Comedy", "Drama"]},
    ]), encoding="utf-8")
    (pack_dir / "creatives.json").write_text(json.dumps([
        {"name": "Christopher Nolan", "role_kind": "Director", "sex": "Male", "fame": "Legend", "genre_specialty": "Sci-fi"},
    ]), encoding="utf-8")
    (pack_dir / "studios.json").write_text(json.dumps([
        {"name": "A24", "kind": "Movie", "tier": "B"},
        {"name": "Universal Pictures", "kind": "Movie", "tier": "A"},
        {"name": "HBO", "kind": "Cable", "tier": "Cable"},
    ]), encoding="utf-8")

    engine = HollywoodlandEngine(seed=12, roster_pack=str(pack_dir))
    assert engine.active_roster_name == "Test Real World Pack"
    names = {a.name for a in engine.actors.values()}
    assert "Cillian Murphy" in names and "Emma Stone" in names
    # Verify attributes were auto-filled cleanly in 1..100
    for a in engine.actors.values():
        assert len(a.attributes) == len(CORE_ATTRIBUTES)
        assert all(1 <= v <= 100 for v in a.attributes.values())
    creative_names = {c.name for c in engine.creatives.values()}
    assert "Christopher Nolan" in creative_names
    movie_studios = {f.studio_or_channel for f in engine.films.values() if f.series_or_movie == "Movie"}
    assert movie_studios <= {"A24", "Universal Pictures"}
