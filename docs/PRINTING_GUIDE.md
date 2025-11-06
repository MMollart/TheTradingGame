# 📄 Printing Player Instructions

This guide explains how to convert the player instructions to a printable format.

## 📋 Choose Your Version

**Two versions available:**

1. **PLAYER_INSTRUCTIONS_QUICK.md** (2 pages) - **RECOMMENDED for most players**
   - Condensed quick reference with all essential information
   - Fits on 2 pages when printed
   - Perfect for distributing to all players
   - Tables and bullet points for quick scanning

2. **PLAYER_INSTRUCTIONS.md** (15-20 pages) - For game hosts or detailed study
   - Comprehensive guide with examples and strategies
   - Better as a reference document or host guide
   - Include detailed explanations and troubleshooting

## Quick Print Options

### Option 1: GitHub Markdown Preview (Easiest)
1. View `PLAYER_INSTRUCTIONS_QUICK.md` (or `PLAYER_INSTRUCTIONS.md`) on GitHub
2. Click the "Print" button in your browser
3. Save as PDF or print directly

### Option 2: Markdown to PDF Tools

#### Using Pandoc (Recommended)
```bash
# Install pandoc (if not already installed)
# macOS:
brew install pandoc

# Ubuntu/Debian:
sudo apt-get install pandoc

# Convert Quick Guide (2 pages)
pandoc docs/PLAYER_INSTRUCTIONS_QUICK.md -o player-quick-guide.pdf \
  --pdf-engine=xelatex \
  -V geometry:margin=0.75in

# Or convert Complete Guide (15-20 pages)
pandoc docs/PLAYER_INSTRUCTIONS.md -o player-instructions.pdf \
  --pdf-engine=xelatex \
  --toc \
  -V geometry:margin=1in

# Or convert to HTML first for better formatting
pandoc docs/PLAYER_INSTRUCTIONS_QUICK.md -o player-quick-guide.html \
  -s --toc \
  --css=https://cdn.jsdelivr.net/npm/github-markdown-css/github-markdown.min.css

# Then open in browser and print to PDF
```

#### Using Markdown to PDF Online Tools
1. Go to https://www.markdowntopdf.com/
2. Upload `PLAYER_INSTRUCTIONS.md`
3. Download the generated PDF

#### Using VS Code Extension
1. Install "Markdown PDF" extension in VS Code
2. Open `PLAYER_INSTRUCTIONS.md`
3. Right-click → "Markdown PDF: Export (pdf)"

### Option 3: Copy to Google Docs
1. Copy all content from `PLAYER_INSTRUCTIONS.md`
2. Paste into Google Docs
3. Format as needed
4. File → Download → PDF Document

### Option 4: Copy to Word/Pages
1. Copy all content from `PLAYER_INSTRUCTIONS.md`
2. Paste into Microsoft Word or Apple Pages
3. Format as needed (emojis should work!)
4. Export as PDF

## Printing Tips

### For Best Results:
- **Paper Size**: A4 or Letter (8.5" × 11")
- **Orientation**: Portrait
- **Margins**: 1 inch (2.5 cm) all sides
- **Font**: Use a clear, readable font like Arial or Calibri at 10-12pt
- **Color**: Print in color for emoji visibility (or replace emojis with text)
- **Pages**: Document is ~15-20 pages depending on formatting

### Recommended Printing Settings:
```
Page size: A4/Letter
Orientation: Portrait
Margins: Normal (1" / 2.5cm)
Scale: 100% (or fit to page)
Pages per sheet: 1
Two-sided: Yes (save paper!)
```

### Making it Compact (Optional):
To reduce pages, you can:
- Use smaller margins (0.75" / 2cm)
- Use 10pt font size
- Print two-sided
- Remove some whitespace/sections if needed

## Document Sections

The player instructions include:
1. **Game Overview** - Objectives and basics
2. **Player Roles** - What players, bankers, and hosts do
3. **Your Nation** - All 4 nation types explained
4. **Resources** - All 5 resource types
5. **Buildings** - All 8 building types with costs
6. **Physical Challenges** - How challenges work
7. **Production** - How to produce resources
8. **Trading System** - Bank and team trading
9. **Food Tax & Penalties** - Tax rules and famine
10. **Game Rules** - What you can/can't do
11. **Scoring** - How winners are determined
12. **Strategy Tips** - Early/mid/late game advice

## Printing for Multiple Teams

If running a game with multiple teams (recommended), print:
- **1 copy per team** (4-6 players share one copy)
- **Or 1 copy per 2 players** (more convenient for reference)

Example for a 4-team game (16 players):
- Minimum: 4 copies (1 per team)
- Recommended: 8 copies (1 per 2 players)

## Black & White Printing

If printing in black & white:
- Emojis may not print well
- Section headings still clear with **bold** and `#` symbols
- All content remains readable
- Consider highlighting section headers after printing

## Quick Reference Cards (Optional)

For even simpler printing, consider creating quick reference cards with:
- Building costs
- Challenge types
- Basic rules
- Food tax amounts

These can be 1-2 pages and easier to distribute.

## Digital Distribution

Instead of printing, you can:
1. Share the GitHub link: `docs/PLAYER_INSTRUCTIONS.md`
2. Send a PDF version via email
3. Display on tablets/phones during gameplay
4. Project key sections on a screen

## Support

If you have issues with conversion or printing:
- Check the formatting in the original `.md` file
- Try a different conversion tool
- Reach out via GitHub Issues

---

**Remember**: The goal is to help players understand the game quickly. Feel free to adapt the document to your needs!
