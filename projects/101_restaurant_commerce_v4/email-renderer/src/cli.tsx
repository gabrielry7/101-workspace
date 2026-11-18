import { renderEmail } from "./index";
let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (part) => {
  input += part;
  if (Buffer.byteLength(input) > 131072) {
    process.stderr.write("email_input_limit\n");
    process.exit(1);
  }
});
process.stdin.on("end", async () => {
  try {
    process.stdout.write(JSON.stringify(await renderEmail(JSON.parse(input))));
  } catch {
    process.stderr.write("email_render_invalid_or_failed\n");
    process.exitCode = 1;
  }
});
