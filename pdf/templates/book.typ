// Zúme Training guidebook — matches reference two-column layout:
// left sidebar = section labels + timing + QR (for READ/ACTIVITY);
// right column = reading content. Light-blue rules + dashed section dividers.

#let book = json("book.json")

#let accent = rgb("#1f4e79")
#let rule-blue = rgb("#7eb6d9")
#let muted = rgb("#444444")

#let sidebar-w = 1.65in
#let col-gutter = 0.5in
#let content-inset = 0.55em
#let left-pad = sidebar-w + col-gutter

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
#set par(justify: false, leading: 0.78em, spacing: 0.85em)

#let dashed-rule() = {
  v(0.65em)
  line(length: 100%, stroke: (paint: rule-blue, thickness: 0.75pt, dash: "densely-dashed"))
  v(0.7em)
}

#let sidebar-label(label, duration: none, qr: none) = {
  block(width: 100%, breakable: false)[
    #align(right)[
      #text(weight: "bold", size: 14pt, fill: black)[#upper(label)]
      #if duration != none [
        #linebreak()
        #v(0.15em)
        #text(size: 9.5pt, fill: black)[(#duration)]
      ]
    ]
    #if qr != none and qr != "" [
      #v(0.7em)
      #align(center)[
        #image(qr, width: 1.45in)
      ]
    ]
  ]
}

#let content-panel(body) = {
  block(
    width: 100%,
    breakable: true,
    stroke: (left: 1pt + rule-blue),
    inset: (left: content-inset, top: 0.05em, bottom: 0.15em),
    body,
  )
}

#let bullets(items) = {
  if items == none or items.len() == 0 { return }
  for item in items [
    #block(sticky: true, spacing: 0.28em)[
      #grid(
        columns: (0.85em, 1fr),
        gutter: 0.2em,
        [•],
        [#item],
      )
    ]
  ]
}

/// Section with left sidebar (label/time/optional QR) + flowing right content.
/// Sticky header keeps label (+ QR) with the first content chunk; overflow continues
/// in the right column with the blue rule (matching reference continuation pages).
#let guidebook-section(label, duration: none, qr: none, header: none, body) = {
  dashed-rule()
  // Sticky opener: sidebar + start of content (title / first chunk)
  block(breakable: false, sticky: true, width: 100%, spacing: 0em)[
    #grid(
      columns: (sidebar-w, 1fr),
      column-gutter: col-gutter,
      sidebar-label(label, duration: duration, qr: qr),
      content-panel[
        #if header != none [#header]
        #body
      ],
    )
  ]
}

/// Like guidebook-section but body may be long: put only `lead` in sticky opener,
/// then continue `rest` with matching left indent + rule.
#let guidebook-section-flow(label, duration: none, qr: none, lead, rest) = {
  dashed-rule()
  block(breakable: false, sticky: true, width: 100%, spacing: 0em)[
    #grid(
      columns: (sidebar-w, 1fr),
      column-gutter: col-gutter,
      sidebar-label(label, duration: duration, qr: qr),
      content-panel[#lead],
    )
  ]
  if rest != none [
    #block(
      breakable: true,
      width: 100%,
      inset: (left: left-pad),
      spacing: 0em,
      content-panel[#rest],
    )
  ]
}

#let paras(items) = {
  if items == none { return }
  for p in items [
    #par[#p]
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
  #v(0.55em)

  #for block-data in session.blocks [
    #let kind = block-data.at("kind")

    #if kind == "checkin" [
      // Reference places check-in QR in the RIGHT column under the instruction.
      #guidebook-section(
        block-data.label,
        duration: block-data.at("duration", default: none),
        qr: none,
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
          #v(0.35em)
          #par[#block-data.tools_intro]
          #bullets(block-data.at("tools", default: ()))
        ]
      ]
    ] else if kind == "read" [
      #let ps = block-data.at("paragraphs", default: ())
      #let lead = {
        text(weight: "bold", size: 9.5pt)[#block-data.title]
        v(0.35em)
        if ps.len() > 0 { par[#ps.at(0)] }
        if ps.len() > 1 { par[#ps.at(1)] }
      }
      #let rest = if ps.len() > 2 {
        for p in ps.slice(2) [
          #par[#p]
        ]
      } else { none }
      #guidebook-section-flow(
        block-data.label,
        duration: block-data.at("duration", default: none),
        qr: block-data.at("qr", default: none),
        lead,
        rest,
      )
    ] else if kind == "discuss" [
      #guidebook-section(
        block-data.label,
        duration: block-data.at("duration", default: none),
      )[
        #if block-data.at("intro", default: "") != "" [
          #par[#block-data.intro]
          #v(0.2em)
        ]
        #bullets(block-data.at("questions", default: ()))
      ]
    ] else if kind == "activity" [
      #let lead = {
        text(weight: "bold", size: 9.5pt)[#block-data.title]
        v(0.3em)
        bullets(block-data.at("instructions", default: ()))
      }
      #let body-paras = block-data.at("paragraphs", default: ())
      #let rest = {
        if body-paras.len() > 0 {
          for p in body-paras [
            #par[#p]
          ]
        }
        if block-data.at("worksheet", default: none) == "listof100" [
          #v(0.35em)
          #text(weight: "bold")[List of 100]
          #v(0.2em)
          #text(size: 8.5pt, fill: muted)[Write names below. Mark Disciple / Unbeliever / Unknown.]
          #let count = block-data.at("worksheet_count", default: 100)
          #for i in range(1, count + 1) [
            #block(breakable: false, sticky: true, spacing: 0.2em, width: 100%)[
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
      }
      #guidebook-section-flow(
        block-data.label,
        duration: block-data.at("duration", default: none),
        qr: block-data.at("qr", default: none),
        lead,
        rest,
      )
    ] else if kind == "center" [
      #dashed-rule()
      #block(inset: (left: left-pad), width: 100%)[
        #content-panel[
          #if block-data.at("title", default: none) != none [
            #text(weight: "bold", size: 11pt)[#block-data.title]
            #v(0.3em)
          ]
          #paras(block-data.at("paragraphs", default: ()))
        ]
      ]
    ] else if kind == "image_note" [
      #dashed-rule()
      #block(breakable: false, sticky: true, width: 100%)[
        #grid(
          columns: (sidebar-w, 1fr),
          column-gutter: col-gutter,
          {
            if block-data.at("qr", default: none) != none [
              #align(center)[#image(block-data.qr, width: 1.2in)]
            ]
          },
          content-panel[
            #text(weight: "bold")[#block-data.title]
            #v(0.25em)
            #for p in block-data.at("paragraphs", default: ()) [
              #text(style: "italic", fill: muted)[#p]
            ]
          ],
        )
      ]
    ] else if kind == "obey" [
      #guidebook-section(block-data.label)[
        #bullets(block-data.at("challenges", default: ()))
      ]
    ] else if kind == "congratulations" [
      #dashed-rule()
      #v(0.8em)
      #align(center)[
        #text(size: 16pt, weight: "bold", fill: accent)[#block-data.label]
        #v(0.5em)
        #for p in block-data.at("paragraphs", default: ()) [
          #par[#p]
        ]
        #v(0.45em)
        #if block-data.at("qr", default: none) != none [
          #image(block-data.qr, width: 1.35in)
        ]
      ]
    ]
  ]
]
