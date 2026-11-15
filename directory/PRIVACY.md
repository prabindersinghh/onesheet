# Privacy

onesheet collects no data. It has no server, no analytics and no account.

Everything runs where Claude runs your code: on your computer in Claude Code and Cowork, or in your own code sandbox in claude.ai and the Claude desktop app. The repository you choose, the fact ledger and the PDF stay there.

To build a page it may download public files: the repository you name, if it's a public GitHub URL, and the Python libraries reportlab, pillow, pypdf and pypdfium2 from PyPI if they aren't installed already. It may also read public counts, such as GitHub stars, from public APIs. Those requests carry only what's needed to fetch them, never your code or your page.

Claude itself reads the repository while it works, under your own Claude account and its terms.
