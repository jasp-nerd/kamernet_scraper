# Profiles

A **profile** tells Radar two things:

1. What to search for: city, radius, price cap, listing types, sort order.
2. How to score listings: the scoring prompt the LLM receives.

Both live in a single YAML file in `profiles/`. Switch profiles by setting `PROFILE=<name>` in `.env`, passing `--profile <name>` on the CLI, or pointing at an absolute path to any YAML file.

## Built-in profiles

| Profile                        | Search scope                      | Who it's for                                                  |
| ------------------------------ | --------------------------------- | ------------------------------------------------------------- |
| `generic`                      | Amsterdam + 10 km, any price      | Anyone, anywhere. Neutral universal defaults.                 |
| `student-amsterdam`            | Amsterdam + 5 km, ≤ €2300         | Two students/young adults near VU Amsterdam.                  |
| `young-professional-randstad`  | Amsterdam + 25 km, ≤ €2500        | Solo professional, Randstad-wide, apartments/studios only.    |
| `family-utrecht`               | Utrecht + 15 km, ≤ €3000, ≥ 60 m² | Family of 4, Utrecht + suburbs, 2+ bedrooms, long-term only.  |

## Writing your own

Copy an existing profile and edit:

```bash
cp profiles/generic.yaml profiles/my-situation.yaml
# edit it
PROFILE=my-situation python -m radar run --once --dry-run
```

### Schema

```yaml
# Human-readable identifier. Shows up in logs and the dashboard.
name: my-situation
description: One-line description shown in `radar list-profiles`.

search:
  # Kamernet URL slug, the part after /huren/ (https://kamernet.nl/huren/<slug>).
  # Examples: huurwoningen-amsterdam, huurwoningen-rotterdam, kamers-utrecht.
  city_slug: huurwoningen-amsterdam

  # Search radius in km around the city.
  radius_km: 10

  # Upper bound on monthly rent (EUR). 0 = no cap.
  max_rent: 0

  # Minimum surface area in m². 0 = no minimum.
  min_size: 0

  # newest | price_asc | price_desc
  sort: newest

  # Types to include.
  # 1 = Room (in shared house)
  # 2 = Apartment (self-contained)
  # 3, 4 = Studio (self-contained)
  listing_types: [1, 2, 3, 4]

scoring_prompt: |
  <free-form prompt, one multi-line string>

  The prompt receives a {listing_data} placeholder that Radar replaces with
  the listing's structured fields (price, surface, postal code, description,
  etc.) at scoring time.

  End with an instruction to respond with valid JSON:
  Respond with ONLY valid JSON:
  {{"score": <integer 0-100>, "reasoning": "<1-2 sentences>"}}
```

### Writing a good scoring prompt

The LLM gets your prompt plus a structured listing block. Good prompts:

1. State the user's situation up top in 1-2 sentences.
2. Call out deal-breakers explicitly ("cap score at 15 if the listing says X").
3. Break scoring into weighted categories (Price Value 0-30, Location 0-25, Quality 0-20, …). Tell the model how many points per band.
4. Give concrete examples, especially for location. List specific postal codes or neighborhoods with their scores.
5. Demand specific reasoning ("reference specific fields you used"), or you'll get generic fluff.
6. Include `{listing_data}` somewhere in the prompt. Radar substitutes this in.

See `profiles/student-amsterdam.yaml` for a fully worked example.

### Local-only profiles

Add `.local.yaml` to the filename and `.gitignore` skips it:

```
profiles/my-profile.local.yaml
```

Use this for profiles with sensitive notes you don't want to publish.

## Contributing a profile

If your profile would help other users (a new city, a new demographic), open a PR. See `CONTRIBUTING.md` for the starter list: `profiles/amsterdam-expat.yaml`, `profiles/rotterdam-student.yaml`, `profiles/the-hague-government.yaml`, and similar.

Rules for contributed profiles:
- No personal identifiers (names, specific addresses, phone numbers).
- No commercial references (specific employer names, school names as deal-breakers).
- The rubric text should explain itself. Reviewers should understand why a listing got its score from the prompt alone.

## Tweaking the rubric iteratively

Fastest dev loop:

```bash
python -m radar run --once --dry-run --profile my-situation -v
```

This scrapes, scores, and prints everything, but skips DB writes and notifications. Edit the YAML, re-run, compare scores. Once you're happy, drop `--dry-run` and let it run for real.

If you already have listings in the DB and want to re-score them all with a new rubric:

```bash
python -m scripts.rescore --profile my-situation
```
