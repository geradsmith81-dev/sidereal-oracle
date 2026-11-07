# The Sidereal Oracle: home-screen launcher

This small page gives **The Sidereal Oracle** an app icon on iPhone, iPad and Android.
Open it, choose "Add to Home Screen", and the astrolabe icon opens the Oracle.

The Oracle itself runs at https://sidereal-lilly-chart-8aevvdj4xjfdczxjz7swbt.streamlit.app/

Files: `index.html` (the page), `manifest.webmanifest` (name, icon and colours for Android),
`sw.js` (keeps this page available offline), `icons/` (app icons), `.nojekyll` (tells GitHub Pages
to publish the files as they are).

To point the launcher at a different address, edit the line `var APP_URL = "...";` in `index.html`.
