"""Run an explicit local owner-connection demo, with zero Google requests."""
import argparse
from pathlib import Path
from cryptography.fernet import Fernet
import uvicorn
from .api import create_app
from .campaign_demo import seed_campaign_demo, PASSWORD
from .connections import ConnectionRuntime
from .connection_google import FakeGoogleBusinessAdapter


def app_for_demo(database_url, key, *, worker=True):
    runtime = ConnectionRuntime(FakeGoogleBusinessAdapter(), key, worker=worker)
    app = create_app(database_url=database_url, demo_mode=True, environment='development',
                     connections_runtime=runtime, payment_recovery_enabled=False)
    with app.state.session_factory() as session:
        seed_campaign_demo(session)
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='/tmp/101-connections-demo.db')
    parser.add_argument('--port', type=int, default=8804)
    args = parser.parse_args()
    key_path = Path(args.db + '.demo-key')
    if not key_path.exists():
        with key_path.open('xb') as f:
            key_path.chmod(0o600)
            f.write(Fernet.generate_key())
    app = app_for_demo('sqlite:///' + str(Path(args.db).resolve()), key_path.read_bytes())
    print(f'DEMO ONLY: http://127.0.0.1:{args.port}/connections')
    print('Owner: campaign.manager ;', PASSWORD)
    print('Synthetic Google data only. No external connections or messages.')
    uvicorn.run(app, host='127.0.0.1', port=args.port, access_log=False)


if __name__ == '__main__':
    main()
