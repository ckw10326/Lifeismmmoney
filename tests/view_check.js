const fs = require("fs");
const app = require("../js/app.js");

const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const output = { urls: input.urls.map((href) => app.catalogUrl(href)), hrefs: input.hrefs.map((href) => app.safeHref(href)) };
for (const [name, catalog] of Object.entries(input.catalogs)) {
  output[name] = {};
  for (const asOf of input.as_ofs) {
    output[name][asOf] = app.viewModel(catalog, asOf);
  }
}
fs.writeFileSync(process.argv[3], JSON.stringify(output));
