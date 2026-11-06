# Publishing the prepared GitHub Wiki

This folder stores a ready-to-publish GitHub Wiki. The connected GitHub repository API can update the main code repository but **cannot directly create or edit Wiki pages**; Wiki pages live in a separate Git-backed repository.

## Browser publishing (the current Wiki is still at Create new page)

1. Open https://github.com/jheinrichk/Command-Modern-Operations-CMO-LLM-Bridge/wiki/_new .
2. Set the Title to **Home**.
3. Open [Home.md](Home.md) in the repository, select **Raw**, copy its full text and paste into Page content.
4. Click **Save page**. This initializes the Wiki.
5. Use **New Page** to publish each other page, setting its title to the exact filename without `.md`: Getting Started, CONN Interface, Scenario Development Workflow, Knowledge Pack and RAG, Automation and Safety, Play Modes and IKE, Scenario Showcase, Architecture, and Troubleshooting.
6. Create **_Sidebar** and **_Footer** as pages with the contents of `_Sidebar.md` and `_Footer.md`. GitHub renders these as navigation/sidebar/footer.
7. Verify the image loads and every page link resolves.

## One-command publishing after initialization (Windows)

With Git for Windows installed and your GitHub authentication configured, clone or update the **main repository** locally. Once you have manually saved the first Home page in the GitHub Wiki, run this from the repository folder:

§§§powershell
powershell -ExecutionPolicy Bypass -File .\wiki-source\Publish-CMOWiki.ps1
§§§

The script clones the Wiki into a temporary folder, copies the 12 prepared Markdown pages (10 content pages plus sidebar and footer), creates a regular commit and pushes to the existing Wiki default branch. It does **not** force push or delete unrelated pages. If the Wiki has not been initialized, cloning fails with a prompt to save Home first.

## Faster option: git-backed GitHub Wiki

After the initial Home page is saved, GitHub exposes the Wiki Git remote:

```powershell
git clone https://github.com/jheinrichk/Command-Modern-Operations-CMO-LLM-Bridge.wiki.git
# Copy the Markdown files from this wiki-source folder (except PUBLISHING.md)
cd Command-Modern-Operations-CMO-LLM-Bridge.wiki
git add .
git commit -m "Publish CMO LLM Bridge documentation and scenario showcase"
git push origin master
```

Check the Wiki's actual default branch after cloning; it can differ from the main code repository's `main` branch. Authentication with Wiki push permission is required. Do not overwrite a Wiki page someone else has edited without reviewing the diff.

This document is only a publishing guide; it should not be published as a Wiki page.
