"""Local synthetic social workflow; never use this seed for a real merchant."""
import argparse
from pathlib import Path
import uvicorn
from world_model.restaurant_commerce.db import make_engine, init_schema, session_factory
from world_model.restaurant_commerce.social_production import upgrade
from world_model.restaurant_commerce.campaign_demo import seed_campaign_demo
from world_model.restaurant_commerce.api import create_app

parser=argparse.ArgumentParser()
parser.add_argument('--db',required=True)
parser.add_argument('--port',type=int,default=8832)
args=parser.parse_args()
engine=make_engine('sqlite:///'+str(Path(args.db).resolve()))
init_schema(engine)
upgrade(engine)
with session_factory(engine)() as session:
    seed_campaign_demo(session)
app=create_app(engine=engine,demo_mode=True,payment_recovery_enabled=False)
uvicorn.run(app,host='127.0.0.1',port=args.port)
