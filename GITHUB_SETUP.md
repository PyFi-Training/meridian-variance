# Loading Meridian Variance into GitHub

Follow these steps exactly. Takes about 10 minutes.

---

## Step 1 — Create the repo on GitHub

1. Go to [github.com/PyFi-Training](https://github.com/PyFi-Training) and sign in
2. Click the green **New** button (top left)
3. Set:
   - **Repository name:** `meridian-variance`
   - **Description:** `AI-powered variance analysis demo — PyFi`
   - **Visibility:** Public
   - **Do NOT** tick "Add a README file" — you already have one
4. Click **Create repository**
5. Copy the repo URL shown — it will look like:
   `https://github.com/PyFi-Training/meridian-variance.git`

---

## Step 2 — Unzip and navigate to the folder

Unzip `meridian-variance.zip` on your Mac. Open Terminal and navigate into it:

```bash
cd ~/Downloads/meridian-variance
```

Confirm you can see the files:

```bash
ls
# Should show: app.py  data/  notebooks/  pyproject.toml  README.md  requirements.txt  src/
```

---

## Step 3 — Initialise git and push

Run these commands one at a time in Terminal:

```bash
# Initialise a git repo in the folder
git init

# Stage all files
git add .

# First commit
git commit -m "Initial commit — Meridian variance analysis demo"

# Point to the GitHub repo you just created
git remote add origin https://github.com/PyFi-Training/meridian-variance.git

# Push to GitHub
git branch -M main
git push -u origin main
```

If prompted for credentials, use your GitHub username and a **Personal Access Token** (not your password). To create a token: GitHub → Settings → Developer Settings → Personal Access Tokens → Tokens (classic) → Generate new token. Give it `repo` scope.

---

## Step 4 — Verify

Go to `https://github.com/PyFi-Training/meridian-variance` in your browser. You should see the full file tree and the README rendered.

---

## Step 5 — Set up the Streamlit deployment (optional, for the live demo)

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
2. Click **New app**
3. Select repository: `PyFi-Training/meridian-variance`
4. Branch: `main`
5. Main file path: `app.py`
6. Click **Advanced settings** → add secret:
   - Key: `OPENAI_API_KEY`
   - Value: your OpenAI API key
7. Click **Deploy**

Streamlit will build and deploy. Share the URL with your audience — it stays alive as long as it gets traffic (use UptimeRobot to keep it warm).

---

## Updating the repo later

If you make changes to any file:

```bash
git add .
git commit -m "describe what you changed"
git push
```

Streamlit will automatically redeploy when you push to `main`.
