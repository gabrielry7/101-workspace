"""Explicit local signup demo. No real phone or email delivery."""
import argparse
import uvicorn
from .api import create_app
from .campaign_demo import seed_campaign_demo, PASSWORD
from .customer_signup_delivery import FakePhoneVerifier


def app_for_demo(database_url, origin='http://127.0.0.1:8803'):
    options = {'mode': 'test', 'public_origin': origin,
               'adapters': {'phone': FakePhoneVerifier(), 'email': FakePhoneVerifier('synthetic-email-only')},
               'allowed_regions': ['CO', 'US', 'MX', 'ES']}
    app = create_app(database_url=database_url, demo_mode=True, environment='development',
                     signup_options=options, payment_recovery_enabled=False)
    with app.state.session_factory() as session:
        seed_campaign_demo(session)
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='/tmp/101-signup-demo.db')
    parser.add_argument('--port', type=int, default=8803)
    args = parser.parse_args()
    origin = f'http://127.0.0.1:{args.port}'
    app = app_for_demo('sqlite:///' + args.db, origin)
    print('DEMO ONLY:', origin + '/join/honorato-campaign-test')
    print('Owner:', origin + '/customers/signup', '; campaign.manager ;', PASSWORD)
    print('Codes appear on screen. No real messages. Local QR is not public.')
    uvicorn.run(app, host='127.0.0.1', port=args.port, access_log=False)


if __name__ == '__main__':
    main()
