// Zúme Training guidebook — matches reference two-column layout:
// left sidebar = section labels + timing + QR (for READ/ACTIVITY);
// right column = reading content. Light-blue rules + dashed section dividers.
//
// QR is #place'd in the left rail so right-column text keeps flowing beside
// (and past) it — no empty full-height band reserved for the QR row.

#let book = json("book.json")

#let accent = rgb("#1f4e79")
#let rule-blue = rgb("#7eb6d9")
#let muted = rgb("#444444")

#let sidebar-w = 1.65in
#let col-gutter = 0.5in
#let content-inset = 0.55em
#let left-pad = sidebar-w + col-gutter
#let qr-size = 1.45in

#set document(
  title: book.title + " — " + book.subtitle,
  author: "Zúme Project",
)
#set page(
  paper: "us-letter",
  margin: (top: 0.6in, bottom: 0.7in, left: 0.45in, right: 0.55in),
  numbering: none,
)
#set text(font: "Liberation Sans", size: 9.5pt, fill: black, lang: book.lang)
// Paragraph breathing room (Chris feedback #3)
#set par(justify: false, leading: 0.85em, spacing: 1.35em)

// Horizontal dashed divider with clear padding above/below (Chris feedback #1)
#let dashed-rule() = {
  v(1.45em)
  line(length: 100%, stroke: (paint: rule-blue, thickness: 0.75pt, dash: "densely-dashed"))
  v(1.5em)
}

#let sidebar-label-only(label, duration: none) = {
  align(right)[
    #text(weight: "bold", size: 14pt, fill: black)[#upper(label)]
    #if duration != none [
      #linebreak()
      #v(0.2em)
      #text(size: 9.5pt, fill: black)[(#duration)]
    ]
  ]
}

#let content-panel(body) = {
  block(
    width: 100%,
    breakable: true,
    stroke: (left: 1pt + rule-blue),
    inset: (left: content-inset, top: 0.05em, bottom: 0.2em),
    body,
  )
}

#let bullets(items) = {
  if items == none or items.len() == 0 { return }
  for item in items [
    #block(sticky: true, spacing: 0.4em)[
      #grid(
        columns: (0.85em, 1fr),
        gutter: 0.2em,
        [•],
        [#item],
      )
    ]
  ]
}

#let paras(items) = {
  if items == none { return }
  for p in items [
    #par[#p]
  ]
}

/// Short sections without a left-rail QR: label | content grid.
#let guidebook-section(label, duration: none, body) = {
  dashed-rule()
  block(breakable: false, sticky: true, width: 100%, spacing: 0em)[
    #grid(
      columns: (sidebar-w, 1fr),
      column-gutter: col-gutter,
      align(top, sidebar-label-only(label, duration: duration)),
      align(top, content-panel(body)),
    )
  ]
}

/// Sections with a left-rail QR (READ / ACTIVITY).
/// Label + QR are placed in the left rail; ALL body text flows in the right
/// column beside and below the QR (Chris feedback #2).
#let guidebook-section-qr(label, duration: none, qr: none, body) = {
  dashed-rule()
  block(breakable: true, width: 100%, spacing: 0em)[
    // Left rail: label + optional QR (does not force right column height)
    #place(top + left, dy: 0pt)[
      #box(width: sidebar-w)[
        #sidebar-label-only(label, duration: duration)
        #if qr != none and qr != "" [
          #v(0.75em)
          #align(center)[
            #image(qr, width: qr-size)
          ]
        ]
      ]
    ]
    // Right column: full flowing content
    #block(inset: (left: left-pad), width: 100%, breakable: true, spacing: 0em)[
      #content-panel(body)
    ]
  ]
}

// ---------- Cover (reference artwork) ----------
#page(margin: 0pt, numbering: none)[
  #align(center + horizon)[
    #image("cover-10.png", width: 100%, height: 100%, fit: "cover")
  ]
]

// blank page 2 like reference (cover art verso / spacer)
#page(numbering: none)[]

#set page(numbering: "1", footer: context {
  let n = counter(page).get().first()
  align(center, text(size: 10pt, fill: black)[#n])
})
#counter(page).update(3)

// ---------- Sessions ----------
#for session in book.sessions [
  #pagebreak(weak: false)

  // Session header: logo + title (reference centers these)
  #align(center)[
    #image("zume-logo.png", width: 2.4in)
    #v(0.35em)
    #text(size: 14pt, weight: "bold", fill: black)[#session.title]
  ]
  #v(0.7em)

  #for block-data in session.blocks [
    #let kind = block-data.at("kind")

    #if kind == "checkin" [
      // Reference places check-in QR in the RIGHT column under the instruction.
      #guidebook-section(
        block-data.label,
        duration: block-data.at("duration", default: none),
      )[
        #par[#block-data.instruction]
        #if block-data.at("qr", default: none) != none [
          #v(0.7em)
          #align(left)[
            #image(block-data.qr, width: 1.7in)
          ]
          #v(0.55em)
        ]
        #par[#block-data.url_hint #text(weight: "bold")[#block-data.code]]
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
          #par[#block-data.concepts_intro]
          #bullets(block-data.at("concepts", default: ()))
        ]
        #if block-data.at("tools_intro", default: "") != "" [
          #v(0.45em)
          #par[#block-data.tools_intro]
          #bullets(block-data.at("tools", default: ()))
        ]
      ]
    ] else if kind == "read" [
      #guidebook-section-qr(
        block-data.label,
        duration: block-data.at("duration", default: none),
        qr: block-data.at("qr", default: none),
      )[
        #text(weight: "bold", size: 9.5pt)[#block-data.title]
        #v(0.45em)
        #paras(block-data.at("paragraphs", default: ()))
      ]
    ] else if kind == "discuss" [
      #guidebook-section(
        block-data.label,
        duration: block-data.at("duration", default: none),
      )[
        #if block-data.at("intro", default: "") != "" [
          #par[#block-data.intro]
          #v(0.25em)
        ]
        #bullets(block-data.at("questions", default: ()))
      ]
    ] else if kind == "activity" [
      #guidebook-section-qr(
        block-data.label,
        duration: block-data.at("duration", default: none),
        qr: block-data.at("qr", default: none),
      )[
        #text(weight: "bold", size: 9.5pt)[#block-data.title]
        #v(0.4em)
        #bullets(block-data.at("instructions", default: ()))
        #paras(block-data.at("paragraphs", default: ()))
        #if block-data.at("worksheet", default: none) == "listof100" [
          #v(0.45em)
          #text(weight: "bold")[List of 100]
          #v(0.25em)
          #text(size: 8.5pt, fill: muted)[Write names below. Mark Disciple / Unbeliever / Unknown.]
          #let count = block-data.at("worksheet_count", default: 100)
          #for i in range(1, count + 1) [
            #block(breakable: false, sticky: true, spacing: 0.28em, width: 100%)[
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
        ]
      ]
    ] else if kind == "center" [
      #dashed-rule()
      #block(inset: (left: left-pad), width: 100%)[
        #content-panel[
          #if block-data.at("title", default: none) != none [
            #text(weight: "bold", size: 11pt)[#block-data.title]
            #v(0.35em)
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
        )[
          #text(weight: "bold")[#block-data.title]
          #v(0.3em)
          #for p in block-data.at("paragraphs", default: ()) [
            #text(style: "italic", fill: muted)[#p]
          ]
        ]
      ] else [
        #dashed-rule()
        #block(inset: (left: left-pad), width: 100%)[
          #content-panel[
            #text(weight: "bold")[#block-data.title]
            #v(0.3em)
            #for p in block-data.at("paragraphs", default: ()) [
              #text(style: "italic", fill: muted)[#p]
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
          #par[#p]
        ]
        #v(0.5em)
        #if block-data.at("qr", default: none) != none [
          #image(block-data.qr, width: 1.35in)
        ]
      ]
    ]
  ]
]
