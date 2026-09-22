# Apollo Brand Intelligence — Project Guidelines & Mandatory Rules

## CRITICAL RULE: GitHub Updates & Release Packaging
Whenever the user asks to "update GitHub", "upload to GitHub", "push to GitHub", "make the exe", or "create a release":

1. **NEVER just push git commits without the compiled ZIP release.**
2. **Mandatory Full Workflow**:
   - **Step 1: Build the Executable**: Run `build_exe.bat` to compile `dist/Apollo Brand Intelligence/`.
   - **Step 2: Package & Publish GitHub Release**: Run `python release.py` (or specify `--version vX.Y.Z` if incrementing version). This automatically:
     - Syncs and commits source changes to git (`origin main`).
     - Compresses the entire compiled `dist/Apollo Brand Intelligence` directory into `ApolloBrandIntelligence-vX.Y.Z.zip`.
     - Publishes a new GitHub Release or uploads the zip asset to the existing release on GitHub via `gh release`.
   - **Step 3: Verification**: Verify that `gh release list` and `gh release view <tag>` show the release and the attached `.zip` asset.
   - **Step 4: Report**: Provide the direct GitHub release download link (`https://github.com/evildub/Apollo-Brand-Intelligence/releases/tag/<tag>`) and confirm the attached zip file in the final response.

## General Development Rules
- Run `python run_tests.py` before releasing to guarantee 100% test pass rate.
- Preserve all existing comments, docstrings, and architectural invariants across all 19 scraper engines.
