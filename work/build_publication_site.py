#!/usr/bin/env python3
"""Create standalone interactive pages and the public project landing page."""

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
VIZ = ROOT / "publication" / "interactive"
DOCS = ROOT / "docs"
ASSETS = DOCS / "assets"

BASE_CSS = """
:root{--background:#f7f9fb;--foreground:#17324f;--muted-foreground:#61758d;--border:#cfd9e3;--viz-series-1:#0b8793;--viz-series-2:#d96b2b;--destructive:#cf553b;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color-scheme:light}
*{box-sizing:border-box}body{margin:0;background:var(--background);color:var(--foreground);line-height:1.55}main{width:min(1040px,calc(100% - 32px));margin:0 auto;padding:40px 0 70px}h1{font-size:clamp(2.1rem,6vw,4.8rem);line-height:.98;letter-spacing:-.045em;margin:.25em 0}h2{font-size:clamp(1.45rem,3vw,2.25rem);line-height:1.12;letter-spacing:-.025em;margin:1.7em 0 .6em}p{font-size:1.05rem;max-width:72ch}.kicker{color:#d96b2b;font-size:.78rem;font-weight:800;letter-spacing:.14em;text-transform:uppercase}.lede{font-size:clamp(1.18rem,2vw,1.5rem);max-width:62ch;color:#334e68}.abstract{max-width:78ch;background:white;border-top:4px solid #0b8793;border-bottom:1px solid var(--border);padding:22px 24px;margin:30px 0 38px}.abstract h2{font-size:.82rem;line-height:1;letter-spacing:.13em;text-transform:uppercase;color:#096a74;margin:0 0 12px}.abstract p{margin:0;font-size:1.03rem}.metric{font-size:clamp(2.2rem,7vw,5.5rem);font-weight:800;letter-spacing:-.05em;color:#0b8793;line-height:1}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:28px}.figure{margin:34px 0}.figure img{width:100%;height:auto;border:1px solid var(--border);background:white}.caption{font-size:.9rem;color:var(--muted-foreground);max-width:86ch}.viz-controls{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}.form-label{display:grid;gap:5px;font-size:.83rem;font-weight:700}.form-select,.btn{font:inherit;border:1px solid var(--border);background:white;color:var(--foreground);border-radius:7px;padding:8px 11px}.btn{cursor:pointer}.btn-primary{background:#0b8793;color:white;border-color:#0b8793}.card{background:white;border:1px solid var(--border);border-radius:8px;padding:16px;margin-top:12px}.text-small{font-size:.88rem}.text-muted{color:var(--muted-foreground)}nav{display:flex;gap:20px;flex-wrap:wrap;margin-bottom:34px}nav a,a{color:#096a74;text-underline-offset:3px}.story-step{border-left:4px solid #d96b2b;padding-left:18px;margin:24px 0}.note{background:#eaf3f4;border-left:4px solid #0b8793;padding:16px 18px;margin:28px 0;max-width:76ch}footer{border-top:1px solid var(--border);margin-top:50px;padding-top:20px;color:var(--muted-foreground);font-size:.9rem}@media(max-width:760px){.grid{grid-template-columns:1fr}main{width:min(100% - 22px,1040px);padding-top:24px}.abstract{padding:18px}}
"""


def page(title, body):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>{BASE_CSS}</style></head><body><main>{body}</main></body></html>"""


def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    figures = {
        "household.png": ROOT / "outputs/figures/anonymized_household_destination_story.png",
        "forest.png": ROOT / "outputs/figures/cross_dataset_gis_gain_forest.png",
        "transport.png": ROOT / "outputs/figures/validation_transportability_comparison.png",
        "manuscript.pdf": ROOT / "publication/manuscript/manuscript.pdf",
    }
    for name, source in figures.items():
        shutil.copy2(source, ASSETS / name)

    evidence = (VIZ / "climate-mobility-evidence.html").read_text()
    household = (VIZ / "one-household-journey.html").read_text()
    (DOCS / "evidence.html").write_text(page("Test the destination models", '<nav><a href="index.html">Return to the main story</a></nav>' + evidence))
    (DOCS / "household.html").write_text(page("Faridpur to Manikganj", '<nav><a href="index.html">Return to the main story</a></nav>' + household))

    body = """
<nav><a href="#case">Household</a><a href="#results">Results</a><a href="household.html">Household map</a><a href="evidence.html">Model checks</a><a href="assets/manuscript.pdf">Full paper</a></nav>
<p class="kicker">Bangladesh climate mobility</p>
<h1>After river erosion,<br>where does a household go?</h1>
<section class="abstract" aria-labelledby="abstract-heading"><h2 id="abstract-heading">Abstract</h2><p>Most climate-migration research asks whether environmental damage makes people move. This study begins after movement and asks which district receives the mover. In the national BIHS sample, 1,857 migrants come from all 64 origin districts. Adding flood history, built surface, travel time to a city, and cropland to distance and population improves held-out destination prediction by 0.108 log-loss units; the gain remains 0.101 when each origin is excluded from training and 0.094 in a later-wave test. Separate climate samples produce gains of 0.098 for 123 BIHS moves attributed to erosion-related land loss and 0.108 for 184 shock-linked BEMP relocations. Prior BEMP research studies whether shocks change migration likelihood, type, and distance. This project instead conditions on a recorded move and predicts its destination. The estimates are predictive, and the public locations stop at the district level.</p></section>
<p class="lede">One BIHS household reported losing land or homestead land to river erosion. Its head moved from Faridpur to Manikganj in 2010. That recorded move gives the analysis a concrete test: can a model pick Manikganj from the country's 64 districts?</p>
<div class="figure"><img src="assets/household.png" alt="Map of Bangladesh showing an anonymized 2010 move from Faridpur to Manikganj after river-erosion land loss. The distance-and-population model gives Manikganj 7.0 percent probability and rank 6. Adding four GIS measures raises it to 13.7 percent and rank 2."><p class="caption">The model assigns probabilities to candidate districts. The illustration uses the recorded origin, destination, year, and reason for moving. It contains no name or address.</p></div>
<section id="case"><h2>A move the survey can document</h2><div class="story-step"><p><strong>Recorded loss.</strong> River erosion cost the household land or homestead land.</p></div><div class="story-step"><p><strong>Recorded move.</strong> The household head left Faridpur for Manikganj in 2010.</p></div><div class="story-step"><p><strong>Model test.</strong> Manikganj competes with every other district using the same information for each candidate.</p></div><p>The survey does not record the family's private discussion, finances, or personal ties before the move. The analysis does not fill those gaps.</p></section>
<section id="results"><h2>Adding destination geography moved Manikganj from sixth to second</h2><div class="grid"><div><div class="metric">7.0%</div><p>Distance and population only. Manikganj ranks sixth among 64 districts.</p></div><div><div class="metric">13.7%</div><p>Add flood history, built surface, travel time to a city, and cropland. Manikganj ranks second.</p></div></div><div class="note">Faridpur remains the model's first choice. The GIS measures improve the score for the recorded destination, but they do not reproduce the household's decision or establish why it chose Manikganj.</div></section>
<h2>The broad BIHS sample covers every origin district</h2><p>The wider BIHS sample contains 1,857 migrants from all 64 origin districts. The gain remains about 0.10 when the model leaves each origin out of training and when a 2015 model predicts 2018-19 migrants. This is the project's strongest evidence that the destination pattern is not confined to one river corridor.</p><div class="figure"><img src="assets/transport.png" alt="Comparison of household-grouped, origin-held-out, and later-wave tests. The broad BIHS migrant estimates stay near a 0.10 gain. Climate-specific full-choice estimates are weaker when an entire origin is excluded."><p class="caption">Destination rankings transfer across origins more reliably than boundary-crossing predictions. Whether a household crosses a district boundary still depends on local origin conditions.</p></div>
<h2>The gain also appears in two climate-specific samples</h2><p>For 123 BIHS moves attributed to river-erosion land loss, the GIS model improves held-out log loss by 0.098. For 184 BEMP relocations that follow a recorded flood or erosion shock, the gain is 0.108. BEMP gives the stronger shock-to-move sequence; BIHS provides the independent replication.</p><div class="figure"><img src="assets/forest.png" alt="Eight held-out comparisons between a distance-and-population model and a model that adds district GIS measures. All eight point estimates are positive. The BEMP interdistrict interval crosses zero; the other seven displayed intervals are above zero."><p class="caption">Each dot is the average held-out gain over the distance-and-population model. Lines show paired 95 percent household-cluster bootstrap intervals.</p></div>
<p>Use the <a href="household.html">household map</a> to compare all 64 candidate probabilities. Use the <a href="evidence.html">model-check page</a> to change the validation split and candidate set.</p>
<footer>Shail Belani, Undergraduate Researcher, Northwestern University. All results use public district-level geography and are conditional on a recorded move.</footer>
"""
    (DOCS / "index.html").write_text(page("Where do climate-affected households go?", body))
    print(DOCS / "index.html")


if __name__ == "__main__":
    main()
