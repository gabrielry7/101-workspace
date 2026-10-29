import argparse
import datetime
import json
import pathlib

from playwright.sync_api import sync_playwright

p = argparse.ArgumentParser()
p.add_argument("--config", type=pathlib.Path, required=True)
p.add_argument("--output", type=pathlib.Path, required=True)
a = p.parse_args()
c = json.loads(a.config.read_text())
start = datetime.datetime.now(datetime.UTC).isoformat()
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/usr/bin/chromium", headless=True)
    page = b.new_page()
    login = page.request.post(
        c["base_url"] + "/api/staff/login",
        data={"username": "synthetic.single", "password": c["staff_password"]},
        headers={"X-101-Login": "1"},
    )
    assert login.status == 200, "Real staff login failed"
    assert page.request.get(c["base_url"] + "/api/staff/me").status == 200
    # Keep the real request and response; inject a stalled body reader that respects abort.
    page.add_init_script("""(() => {const original=window.fetch;window.fetch=async (url,options={})=>{
   const response=await original(url,options);
   if(String(url)==='/api/staff/me'){
     const realJSON=response.json.bind(response);
     response.json=async()=>{await realJSON();return new Promise((resolve,reject)=>{
       options.signal.addEventListener('abort',()=>reject(new DOMException('Controlled stalled body','AbortError')),{once:true});
     });};
   }
   return response;
 };})();""")
    page.goto(c["base_url"] + "/admin")
    page.wait_for_timeout(17000)
    message = page.locator("#staffStatus").inner_text()
    passed = "Sin conexión" in message
    result = {
        "scenario": "Real HTTP staff session response with injected stalled body reader",
        "revision": c["revision"],
        "start": start,
        "end": datetime.datetime.now(datetime.UTC).isoformat(),
        "target": c["base_url"],
        "execution": "COMPLETE",
        "outcome": "PASS" if passed else "FAIL",
        "message": message,
        "budget_seconds": 17,
        "authenticated_setup": True,
        "network_request": "real backend, body reader fault injected in browser",
        "command": [
            "python",
            "adversarial/staff_deadline.py",
            "--config",
            "<private-run-config>",
            "--output",
            str(a.output),
        ],
    }
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    b.close()
    print(result["outcome"])
    raise SystemExit(0 if passed else 1)
