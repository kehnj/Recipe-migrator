# "Save to AnyList" iPhone Shortcut

When it's set up, saving a recipe takes two taps:

1. In TikTok: **Share → More (•••) → Save to AnyList**
2. About 2 minutes later, a share sheet pops up. Tap **AnyList**.

You do this setup once. It takes about 10 minutes.

---

## Part 1: Create a GitHub token (in Safari)

The Shortcut uses this token to start the import. It only allows running this repo's automation.

1. Open https://github.com/settings/personal-access-tokens/new
2. **Token name:** `Recipe Shortcut`
3. **Expiration:** pick the longest option, or "No expiration".
4. **Repository access:** *Only select repositories* → pick **Recipe-migrator**.
5. **Permissions → Repository permissions → Actions:** set to **Read and write**.
   (Leave everything else alone. "Metadata: Read-only" turns on automatically.)
6. Tap **Generate token** and **copy** it. It starts with `github_pat_`. You can't view it again later.

## Part 2: Build the Shortcut (in the Shortcuts app)

Tap **+** to make a new shortcut and name it **Save to AnyList**. To add each action below,
tap **Search Actions** (or "Add Action"), type the name in **bold**, and tap it.

Wherever you see ⟨Variable⟩, tap that field and pick the variable from the bar above the keyboard,
or long-press the field and choose **Select Variable**.

### Let it appear in the Share menu
Tap the **ⓘ** (or the name at the top) → turn on **Show in Share Sheet**.
Back in the editor, the first block says *Receive ___ from Share Sheet*. Tap the input types
and keep only **URLs** and **Text**.

### Action 1: **Random Number**
- Minimum `100000`, Maximum `999999999`

### Action 2: **Get Contents of URL** (starts the import)
- URL: `https://api.github.com/repos/kehnj/Recipe-migrator/actions/workflows/import-recipe.yml/dispatches`
- Tap **Show More**:
  - **Method:** `POST`
  - **Headers:** add two:
    - `Authorization` → `Bearer github_pat_…` (the word Bearer, a space, then paste your token)
    - `Accept` → `application/vnd.github+json`
  - **Request Body:** `JSON`, then add these fields:
    - `ref` (Text) → `main`
    - `inputs` (Dictionary), and inside it:
      - `url` (Text) → ⟨Shortcut Input⟩
      - `id` (Text) → ⟨Random Number⟩

### Action 3: **Show Notification**
- Text: `Importing recipe… about 2 minutes.`

### Action 4: **Repeat** (change the count to `24`)
Put the following *inside* the Repeat block:

1. **Wait**: `10` seconds
2. **Get Contents of URL**
   - URL: `https://kehnj.github.io/Recipe-migrator/status/`⟨Random Number⟩`.json?try=`⟨Repeat Index⟩
   - (Method stays GET. No headers needed.)
3. **If**: ⟨Contents of URL⟩ **contains** `"status": "done"`
   (type it exactly, with the quotes and the space after the colon)
   - **Get Dictionary Value**: get **Value** for key `url` in ⟨Contents of URL⟩
   - **Share**: ⟨Dictionary Value⟩
   - **Stop This Shortcut**
4. **Otherwise**
   - **If**: ⟨Contents of URL⟩ **contains** `"status": "error"`
     - **Get Dictionary Value**: get **Value** for key `message` in ⟨Contents of URL⟩
     - **Show Alert**: `Couldn't import: ` ⟨Dictionary Value⟩
     - **Stop This Shortcut**
   - **End If**
5. **End If**

### Action 5 (after **End Repeat**): **Show Alert**
- Text: `Still working on it. Open github.com/kehnj/Recipe-migrator/actions to check.`

Tap **Done**.

## Part 3: Try it

1. In TikTok, open a recipe video → **Share** → scroll the bottom row to **More** (or •••) →
   **Save to AnyList**.
   - If it isn't listed, scroll to the bottom of the share sheet → **Edit Actions** → add it.
2. Wait for the share sheet to pop up, then tap **AnyList**.
   - If AnyList isn't in the row, tap **More** and turn it on (you can also drag it to the front).

The first time, iOS asks for permission for the Shortcut to connect to `api.github.com` and
`kehnj.github.io`. Tap **Always Allow** for both.

## Troubleshooting

- **"Couldn't import: …" alert:** the message says what went wrong. Usually the video had no
  recipe in it, or TikTok blocked the download. For those, use the GitHub-issue method in the
  README and attach screenshots.
- **Nothing happens / 401 or 404 error:** the token is wrong or expired, or the `Bearer ` prefix is
  missing. Make a new token (Part 1) and paste it into Action 2.
- **Shortcut gives up after 4 minutes:** GitHub was slow. The recipe is usually ready a minute later.
  Its link is listed at https://kehnj.github.io/Recipe-migrator/
