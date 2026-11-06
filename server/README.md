# Tank server

A small Cloudflare Worker with a D1 database. It gives shared tanks their 6-digit codes.

## Run it on your computer

```bash
npm install
npx wrangler d1 execute desktop-aquarium --local --file schema.sql
npx wrangler dev --port 8799
```

Then, in another window: `python test_worker.py`

## Put it online

```bash
npx wrangler login
npx wrangler d1 create desktop-aquarium
```

Copy the `database_id` it prints into `wrangler.toml`, then:

```bash
npx wrangler d1 execute desktop-aquarium --remote --file schema.sql
npx wrangler deploy
```

Some networks (Xfinity's security filter, for one) block every workers.dev address, so the game uses a
second copy on pages.dev that shares the same database. The workers.dev copy stays because it runs the weekly cleanup.
Pages commands need Wrangler 4.36.0, because newer versions try to send them to Workers instead:

```bash
cd pages
npx wrangler@4.36.0 pages project create desktop-aquarium --production-branch main
npx wrangler@4.36.0 pages deploy public --project-name desktop-aquarium --branch main --commit-dirty=true
```

**After changing `src/worker.js`, deploy both copies.**

Both copies need the same `REPORT_SALT` secret (`wrangler secret put REPORT_SALT` and
`wrangler@4.36.0 pages secret put REPORT_SALT --project-name desktop-aquarium`).

Put `https://desktop-aquarium.pages.dev` in `ONLINE_URL` in `purrfin/version.py`. Opening that address in a browser
shows whether a network can reach the server.

## Looking after it

See how many tanks are shared:

```bash
npx wrangler d1 execute desktop-aquarium --remote --command "SELECT COUNT(*) FROM tanks"
```

Delete a tank (replace 123456 with its code):

```bash
npx wrangler d1 execute desktop-aquarium --remote --command "DELETE FROM tanks WHERE id = '123456'"
```

Each internet address gets 60 wrong codes, 20 new tanks and 20 reports an hour. Tanks reported by 5 different people are hidden automatically. See which ones:

```bash
npx wrangler d1 execute desktop-aquarium --remote --command "SELECT id, updated FROM tanks WHERE hidden = 1"
```

Bring one back:

```bash
npx wrangler d1 execute desktop-aquarium --remote --command "UPDATE tanks SET hidden = 0 WHERE id = '123456'"
```
