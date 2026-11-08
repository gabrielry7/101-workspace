"""Interactive private configuration. Never paste secrets into chat or source files."""
import getpass
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit
from cryptography.fernet import Fernet


def main():
    app_id=input('Instagram application ID: ').strip()
    if not re.fullmatch(r'[0-9]+',app_id):raise SystemExit('Expected the Instagram application ID.')
    secret=getpass.getpass('Instagram application secret (hidden): ').strip()
    uri=input('Exact public HTTPS callback URL [https://app.unocerouno.co/connections/instagram/callback]: ').strip() or 'https://app.unocerouno.co/connections/instagram/callback'
    parsed=urlsplit(uri)
    if (parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or
        parsed.path!='/connections/instagram/callback' or parsed.query or parsed.fragment):
        raise SystemExit('Use https://YOUR-101-HOST/connections/instagram/callback')
    version=input('Graph API version enabled for this app (for example v23.0): ').strip()
    if not re.fullmatch(r'v[0-9]{1,2}\.0',version):raise SystemExit('Use an explicit enabled version.')
    if not secret or any(c in secret+uri for c in '\r\n\x00'):raise SystemExit('Invalid credential/configuration input.')
    path=Path.home()/'.config/101-world-model/instagram-social.env'
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    values={'COMMERCE_INSTAGRAM_CONNECTION_ENABLED':'1','COMMERCE_INSTAGRAM_CLIENT_ID':app_id,
            'COMMERCE_INSTAGRAM_CLIENT_SECRET':secret,'COMMERCE_INSTAGRAM_REDIRECT_URI':uri,
            'COMMERCE_INSTAGRAM_API_VERSION':version,'COMMERCE_INSTAGRAM_CONNECTION_KEY':Fernet.generate_key().decode()}
    # Refuse to replace an existing encryption key and orphan existing credentials.
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w') as output:
        for key,value in values.items():output.write(key+'='+json.dumps(value)+'\n')
    print('Private configuration written to '+str(path)+'. No account is connected yet.')


if __name__=='__main__':main()
