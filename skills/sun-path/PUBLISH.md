# sun-path — Version and publishing

## Version (current: 1.3.0)

- Version is set in the `version` field in the front matter of `SKILL.md`.
- Before publishing, ensure there is no debug or test-only code. Optionally tag in git:  
  `git tag skill/sun-path-v1.3.0`

## Deploy to SSH OpenClaw (VPS)

From your **local** project root (replace with your key path and host):

```bash
rsync -avz -e "ssh -i /path/to/your-key.key" \
  ClawSkills/sun-path/ \
  ubuntu@170.9.8.41:~/.openclaw/skills/sun-path/
```

After syncing, OpenClaw on the VPS will load the new version on the next session; no service restart needed.

## Publish to ClawHub (public install)

**Where to run:** Use your **local machine** (zsh on your Mac), not the VPS. Your repo is the source of truth; publishing from local ensures the exact files you version-control are what get uploaded. The VPS is only for running OpenClaw (deploy with rsync); keep ClawHub publish on your dev machine.

1. **Install CLI and log in** (first time, on your Mac):

   ```bash
   npm i -g clawhub
   clawhub login
   ```
   Follow the prompts (browser or `--token`) to complete login.

2. **Publish this skill** (from your local project root):

   ```bash
   clawhub publish ClawSkills/sun-path --slug sun-path --name "Sun Path & Environmental Analysis" --version 1.3.0 --tags latest --changelog "Annual sun hours, terrain DEM shadow, doc updates"
   ```

   If the slug already exists, this creates a new version. You can omit or shorten `--changelog`.

3. **Later updates**: Bump the version (e.g. to 1.3.1), then run:

   ```bash
   clawhub publish ClawSkills/sun-path --slug sun-path --version 1.3.1 --tags latest --changelog "Bug fix: ..."
   ```

Once published, others can install with `clawhub install sun-path`.

**Note:** Before publishing, set `support_url` and `homepage` in `clawhub.json` to your actual repository URLs.
