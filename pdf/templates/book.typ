// Zúme Training guidebook — reference two-column layout.
// Left rail: section labels, timing, QR. Right: reading content.
//
// QR fix: unbreakable top-aligned grid keeps label+QR with enough right-column
// text so the QR never sits beside an empty band (orphaned at page bottom).

#let book = json("book.json")

#let accent = rgb("#1f4e79")
#let rule-blue = rgb("#7eb6d9")
#let muted = rgb("#444444")

#let sidebar-w = 1.65in
// Balanced gutters around the blue bar: space left of the bar (QR/labels) ≈
// space right of the bar (body text). Right inset is half of the prior 0.42in;
// the freed space moves into col-gutter so content isn’t over-indented and
// left-rail items aren’t flush against the stroke.
#let col-gutter = 0.21in
#let content-inset = 0.21in
#let left-pad = sidebar-w + col-gutter
#let qr-size = 1.35in
// Session header breathing room (~3× prior ~0.55–0.7em top/bottom)
#let session-header-pad = 3em
// Slightly tighter than 1.75em (~3–5pt less) so paragraphs don’t feel loose.
#let para-gap = 1.35em
#let rule-pad-y = 2.6em
#let rule-pad-x = 0.22in

#set document(
  title: book.title + " — " + book.subtitle,
  author: "Zúme Project",
)
#set page(
  paper: "us-letter",
  margin: (top: 0.75in, bottom: 1in, left: 0.45in, right: 0.55in),
  numbering: none,
)
#set text(font: "Liberation Sans", size: 9.5pt, fill: black, lang: book.lang)
#set par(justify: false, leading: 0.82em, spacing: 0.65em)

// Horizontal dashed divider: vertical breathing room + slight horizontal inset
#let dashed-rule() = {
  v(0.35em)
  block(
    width: 100%,
    breakable: false,
    inset: (top: rule-pad-y, bottom: rule-pad-y, x: rule-pad-x),
  )[
    #line(
      length: 100%,
      stroke: (paint: rule-blue, thickness: 0.75pt, dash: "densely-dashed"),
    )
  ]
  v(0.35em)
}

#let sidebar-label-only(label, duration: none) = {
  if label == none or label == "" { return }
  align(right)[
    #text(weight: "bold", size: 14pt, fill: black)[#upper(label)]
    #if duration != none [
      #linebreak()
      #v(0.22em)
      #text(size: 9.5pt, fill: black)[(#duration)]
    ]
  ]
}

#let content-panel(body) = {
  block(
    width: 100%,
    breakable: true,
    stroke: (left: 1pt + rule-blue),
    inset: (left: content-inset, top: 0.1em, bottom: 0.25em),
    body,
  )
}

/// Explicit blank-line-style gap between paragraphs.
/// Use a trailing #v so the gap cannot collapse with adjacent block spacing.
#let para-block(body) = {
  block(width: 100%, breakable: true)[
    #body
  ]
  v(para-gap)
}

#let paras(items) = {
  if items == none { return }
  for p in items [
    #para-block[#p]
  ]
}

#let bullets(items) = {
  if items == none or items.len() == 0 { return }
  for item in items [
    #block(breakable: false, sticky: true, width: 100%)[
      #grid(
        columns: (0.85em, 1fr),
        gutter: 0.2em,
        [•],
        [#item],
      )
    ]
    #v(0.65em)
  ]
}

/// Short sections without left-rail QR.
#let guidebook-section(label, duration: none, body) = {
  dashed-rule()
  block(breakable: false, sticky: true, width: 100%, below: 0.35em)[
    #grid(
      columns: (sidebar-w, 1fr),
      column-gutter: col-gutter,
      // Full-width cell so right-aligned labels hug the blue bar
      align(top, block(width: 100%)[#sidebar-label-only(label, duration: duration)]),
      align(top, content-panel(body)),
    )
  ]
}

/// READ/ACTIVITY with left-rail QR.
/// Unbreakable opener grid: [label+QR | title + enough paragraphs to fill QR height].
/// Remaining paragraphs continue in the right column below (left-padded).
/// This prevents an orphan QR at the bottom of a page with an empty right band.
#let guidebook-section-qr(
  label,
  duration: none,
  qr: none,
  title: none,
  paragraphs: (),
  lead-extra: none,
  rest-extra: none,
  beside-min: 6,
) = {
  dashed-rule()

  // Labels + QR right-aligned to the blue vertical bar (Chris tweak #1).
  // Must be width:100% so align(right) hugs the bar instead of shrink-wrapping left.
  let sidebar = block(width: 100%)[
    #sidebar-label-only(label, duration: duration)
    #if qr != none and qr != "" [
      #v(0.65em)
      #align(right)[
        #image(qr, width: qr-size)
      ]
    ]
  ]

  let n = calc.min(paragraphs.len(), calc.max(beside-min, 1))
  // If few paragraphs, keep all beside the QR
  if paragraphs.len() <= beside-min + 2 {
    n = paragraphs.len()
  }
  let lead = paragraphs.slice(0, n)
  let rest = if paragraphs.len() > n { paragraphs.slice(n) } else { () }

  // Unbreakable: if this won't fit at page bottom, Typst moves the whole opener
  block(breakable: false, sticky: true, width: 100%, below: 0.2em)[
    #grid(
      columns: (sidebar-w, 1fr),
      column-gutter: col-gutter,
      align(top, sidebar),
      align(top, content-panel[
        #if title != none [
          #para-block[#text(weight: "bold", size: 9.5pt)[#title]]
        ]
        #if lead-extra != none [#lead-extra]
        #for p in lead [
          #para-block[#p]
        ]
      ]),
    )
  ]

  if rest.len() > 0 or rest-extra != none [
    #block(
      breakable: true,
      width: 100%,
      inset: (left: left-pad),
      above: 0em,
    )[
      #content-panel[
        #for p in rest [
          #para-block[#p]
        ]
        #if rest-extra != none [#rest-extra]
      ]
    ]
  ]
}

// ---------- Cover ----------
#page(margin: 0pt, numbering: none)[
  #align(center + horizon)[
    #image("cover-10.png", width: 100%, height: 100%, fit: "cover")
  ]
]

#page(numbering: none)[]

#set page(numbering: "1", footer: context {
  let n = counter(page).get().first()
  align(center, text(size: 10pt, fill: black)[#n])
})
#counter(page).update(3)

// ---------- Sessions ----------
#for session in book.sessions [
  #pagebreak(weak: false)

  // Session title block with ~3× top/bottom margin (Chris tweak #3)
  #block(width: 100%, breakable: false, inset: (top: session-header-pad, bottom: session-header-pad))[
    #align(center)[
      #image("zume-logo.png", width: 2.4in)
      #v(0.45em)
      #text(size: 14pt, weight: "bold", fill: black)[#session.title]
    ]
  ]

  #for block-data in session.blocks [
    #let kind = block-data.at("kind")

    #if kind == "checkin" [
      #guidebook-section(
        block-data.label,
        duration: block-data.at("duration", default: none),
      )[
        #para-block[#block-data.instruction]
        #if block-data.at("qr", default: none) != none [
          #v(0.55em)
          #align(left)[
            #image(block-data.qr, width: 1.65in)
          ]
          #v(0.45em)
        ]
        #para-block[#block-data.url_hint #text(weight: "bold")[#block-data.code]]
      ]
    ] else if kind == "pray" [
      #guidebook-section(
        block-data.label,
        duration: block-data.at("duration", default: none),
      )[
        #paras(block-data.at("paragraphs", default: ()))
      ]
    ] else if kind == "look_back" [
      #guidebook-section(
        block-data.label,
        duration: block-data.at("duration", default: none),
      )[
        #paras(block-data.at("paragraphs", default: ()))
      ]
    ] else if kind == "overview" [
      #guidebook-section(
        "OVERVIEW",
        duration: block-data.at("duration", default: none),
      )[
        #if block-data.at("concepts_intro", default: "") != "" [
          #para-block[#block-data.concepts_intro]
          #bullets(block-data.at("concepts", default: ()))
        ]
        #if block-data.at("tools_intro", default: "") != "" [
          #v(0.35em)
          #para-block[#block-data.tools_intro]
          #bullets(block-data.at("tools", default: ()))
        ]
      ]
    ] else if kind == "read" [
      #guidebook-section-qr(
        block-data.label,
        duration: block-data.at("duration", default: none),
        qr: block-data.at("qr", default: none),
        title: block-data.title,
        paragraphs: block-data.at("paragraphs", default: ()),
        beside-min: 7,
      )
    ] else if kind == "discuss" [
      #guidebook-section(
        block-data.label,
        duration: block-data.at("duration", default: none),
      )[
        #if block-data.at("intro", default: "") != "" [
          #para-block[#block-data.intro]
        ]
        #bullets(block-data.at("questions", default: ()))
      ]
    ] else if kind == "activity" [
      #let worksheet = if block-data.at("worksheet", default: none) == "listof100" {
        {
          v(0.35em)
          text(weight: "bold")[List of 100]
          v(0.3em)
          text(size: 8.5pt, fill: muted)[Write names below. Mark Disciple / Unbeliever / Unknown.]
          let count = block-data.at("worksheet_count", default: 100)
          for i in range(1, count + 1) [
            #block(breakable: false, sticky: true, below: 0.3em, width: 100%)[
              #grid(
                columns: (1.5em, 1fr),
                gutter: 0.25em,
                text(size: 9pt)[#i],
                [
                  #box(width: 100%, stroke: (bottom: 0.4pt + luma(160)), inset: (bottom: 0.5em))[]
                  #text(size: 7.5pt, fill: muted)[☐ Disciple   ☐ Unbeliever   ☐ Unknown]
                ],
              )
            ]
          ]
        }
      } else { none }

      #guidebook-section-qr(
        block-data.label,
        duration: block-data.at("duration", default: none),
        qr: block-data.at("qr", default: none),
        title: block-data.title,
        paragraphs: block-data.at("paragraphs", default: ()),
        lead-extra: {
          bullets(block-data.at("instructions", default: ()))
        },
        rest-extra: worksheet,
        beside-min: 5,
      )
    ] else if kind == "center" [
      #dashed-rule()
      #block(inset: (left: left-pad), width: 100%)[
        #content-panel[
          #if block-data.at("title", default: none) != none [
            #para-block[#text(weight: "bold", size: 11pt)[#block-data.title]]
          ]
          #paras(block-data.at("paragraphs", default: ()))
        ]
      ]
    ] else if kind == "image_note" [
      #let qr = block-data.at("qr", default: none)
      #if qr != none [
        #guidebook-section-qr(
          "",
          qr: qr,
          title: block-data.title,
          paragraphs: block-data.at("paragraphs", default: ()),
          beside-min: 3,
        )
      ] else [
        #dashed-rule()
        #block(inset: (left: left-pad), width: 100%)[
          #content-panel[
            #para-block[#text(weight: "bold")[#block-data.title]]
            #for p in block-data.at("paragraphs", default: ()) [
              #para-block[#text(style: "italic", fill: muted)[#p]]
            ]
          ]
        ]
      ]
    ] else if kind == "obey" [
      #guidebook-section(block-data.label)[
        #bullets(block-data.at("challenges", default: ()))
      ]
    ] else if kind == "congratulations" [
      #dashed-rule()
      #v(0.9em)
      #align(center)[
        #text(size: 16pt, weight: "bold", fill: accent)[#block-data.label]
        #v(0.55em)
        #for p in block-data.at("paragraphs", default: ()) [
          #para-block[#p]
        ]
        #v(0.45em)
        #if block-data.at("qr", default: none) != none [
          #image(block-data.qr, width: 1.35in)
        ]
      ]
    ]
  ]
]
