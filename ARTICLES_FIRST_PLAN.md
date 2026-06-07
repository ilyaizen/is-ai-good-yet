# Articles First Layout Plan

> **For Hermes:** Implement this task-by-task, one small change at a time.

**Goal:** Reorder the landing page so the articles section appears before the details section, move details above the footer, and change the veil copy from “Details” to “Articles”.

**Architecture:** This is a presentation-only change in the SvelteKit landing page. The data model stays untouched; we only reorder the rendered sections, update anchor/navigation labels, and adjust the veil label text so the UX matches the new flow. Keep the footer as the terminal section, with details now sitting between articles and footer.

**Tech Stack:** SvelteKit 5, Svelte runes, existing landing components, no backend changes.

---

### Task 1: Confirm the current render order and anchor targets

**Objective:** Verify which component owns the article/details/footer order and which label string drives the veil text.

**Files:**
- Inspect: `src/routes/+page.svelte`
- Inspect: `src/lib/components/landing/verdict-veil.svelte`
- Inspect: `src/lib/components/app-footer.svelte`
- Inspect: `src/lib/components/landing/details-section.svelte`
- Inspect: `src/lib/components/landing/articles-table.svelte`

**Step 1: Read the landing page composition**

Confirm the current order is:
1. verdict hero
2. details section
3. articles table
4. footer

**Step 2: Read the veil copy source**

Find the text constant that renders `Details:` and confirm it is local to the veil component.

**Step 3: Read footer anchors**

Confirm the footer still links to `#details` and `#articles-table` so the new order will remain navigable.

**Verification:**
- No code changes yet.
- We should know exactly which file controls the order and which file controls the veil text.

---

### Task 2: Reorder the landing sections so articles come first

**Objective:** Render the articles section before details, without changing the underlying components.

**Files:**
- Modify: `src/routes/+page.svelte`

**Step 1: Swap the section blocks**

Move the `<div id="articles-table">` block above the `<div id="details">` block inside the content section.

Desired structure:
```svelte
<section id="articles" class="content-section" class:content-section--visible={contentVisible}>
  <div id="articles-table" class="scroll-mt-24">
    <ArticlesTable articles={data.topArticles} />
  </div>

  <div id="details" class="scroll-mt-24">
    <DetailsSection visible={contentVisible} />
  </div>

  <AppFooter />
</section>
```

**Step 2: Keep footer last**

Do not move the footer into a different component; just leave it after both content blocks.

**Step 3: Preserve existing visibility animation**

Leave `contentVisible` and `class:content-section--visible` unchanged so the fade-in still works.

**Verification:**
- The DOM order is now articles → details → footer.
- The `#articles-table` anchor is earlier on the page than `#details`.

---

### Task 3: Update the veil label from “Details” to “Articles”

**Objective:** Change the animated veil title so it says Articles instead of Details.

**Files:**
- Modify: `src/lib/components/landing/verdict-veil.svelte`

**Step 1: Change the label constant**

Replace:
```ts
const LABEL_TEXT = "Details:"
```

with:
```ts
const LABEL_TEXT = "Articles:"
```

**Step 2: Leave the animation logic alone**

Do not rewrite the typing animation, button focus behavior, or token stream.

**Verification:**
- On first render, the veil types `Articles:`.
- No other copy in the veil regresses.

---

### Task 4: Fix navigation text if it now lies about order

**Objective:** Make sure the footer navigation and any in-page labels still make sense after the reorder.

**Files:**
- Modify if needed: `src/lib/components/app-footer.svelte`
- Modify if needed: `src/lib/components/landing/details-section.svelte`

**Step 1: Check footer nav wording**

If the footer says `Details` before `Articles`, leave it alone if it still refers to the section IDs. If any label implies the old visual order, update it.

**Step 2: Check details section header copy**

If the details section has a title or intro that assumes it appears before articles, adjust only the copy, not the data.

**Verification:**
- Anchor labels and section names no longer contradict the new layout.
- No unnecessary refactor of component internals.

---

### Task 5: Verify in-browser and stop when it looks right

**Objective:** Confirm the new order and veil copy in the running app.

**Files:**
- No code changes unless verification reveals a mismatch.

**Step 1: Run the app locally**

Use the project’s normal dev command.

**Step 2: Check the landing page**

Verify:
- veil says `Articles:`
- after reveal, articles appear before details
- footer stays at the bottom
- footer links still jump to the right sections

**Step 3: Commit only if the visual flow matches the request**

**Verification:**
- The page now reads in the order the user asked for.
- The plan is done without backend changes.

---

## Notes

- This is a layout/copy change, not a data change.
- Do not touch the article dataset, verdict math, or pipeline code.
- The only required semantic shift is presentation order and veil wording.

## Suggested commit message

```bash
git commit -m "feat: put articles before details on landing page"
```