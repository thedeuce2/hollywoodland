import argparse
import os
import subprocess
import sys

try:
    import PySide6  # noqa: F401
except ModuleNotFoundError:
    py312 = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python312\python.exe")
    if os.path.exists(py312) and os.path.normcase(sys.executable) != os.path.normcase(py312):
        raise SystemExit(subprocess.call([py312, __file__, *sys.argv[1:]]))
    raise

from hollywoodland.systems.engine import HollywoodlandEngine
from hollywoodland.ui.main_window import launch_hollywoodland


def main() -> None:
    parser = argparse.ArgumentParser(description="HOLLYWOODLAND — Talent Agency & Showbiz Tycoon")
    parser.add_argument("--player", type=str, default="John Doe", help="Manager name")
    parser.add_argument("--agency", type=str, default="Hollywoodland Talent", help="Talent Agency name")
    parser.add_argument("--budget", type=float, default=50000.0, help="Initial agency budget (default: $50,000)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--roster", type=str, default=None, help="Optional Roster Pack name in rosters/ (omit to choose or use default)")
    parser.add_argument("--headless-days", type=int, default=0, help="Run N days headlessly to verify simulation")
    args = parser.parse_args()

    if args.headless_days > 0:
        engine = HollywoodlandEngine(
            player_name=args.player,
            agency_name=args.agency,
            initial_budget=args.budget,
            seed=args.seed,
            roster_pack=args.roster,
        )
        # Sign 3 free agents and submit them to roles
        free_agents = [a for a in engine.actors.values() if a.agency_id is None and a.fame_tier in ("Unknown", "Relatively unknown")][:3]
        for fa in free_agents:
            dem = engine.get_actor_initial_demands(fa.id)
            engine.sign_actor_to_player_agency(fa.id, dem)

        for _ in range(args.headless_days):
            # Auto-resolve any blocking messages in headless mode
            blocker = engine.has_blocking_message()
            if blocker:
                for b in blocker.buttons:
                    if b.command.startswith("ROLE_OFFER:"):
                        _, fid_s, ridx_s, aid_s = b.command.split(":")
                        offer = engine.get_initial_role_offer(int(fid_s), int(ridx_s), int(aid_s))
                        engine.finalize_role_contract(int(fid_s), int(ridx_s), int(aid_s), offer)
                blocker.requires_response = False

            # Submit available clients to matching open roles
            my_clients = [a for a in engine.actors.values() if a.agency_id == 0 and a.schedule_status == "Available"]
            open_films = [f for f in engine.films.values() if f.status == "Casting"]
            for c in my_clients:
                for f in open_films:
                    for r in f.roles:
                        if r.sex == c.sex and c.id not in r.submitted_actor_ids:
                            engine.submit_actor_to_role(c.id, f.id, r.index)
                            break

            engine.advance_day()

        pa = engine.player_agency
        print(f"=== HOLLYWOODLAND Headless Simulation ({engine.pretty_date}) ===")
        print(f"Agency: {pa.name} ({pa.reputation} Tier, Rank #{pa.ranking})")
        print(f"Balance: ${pa.budget:,.0f} | Total Commission Income: ${pa.stats_income:,}")
        print(f"Bookings: {pa.stats_major_roles} Major Roles, {pa.stats_minor_roles} Minor Roles")
        print(f"Messages in Inbox: {len(engine.messages)} | Active Projects: {len(engine.films)}")
        return

    launch_hollywoodland(
        player_name=args.player,
        agency_name=args.agency,
        initial_budget=args.budget,
        seed=args.seed,
        roster_pack=args.roster,
    )


if __name__ == "__main__":
    main()
