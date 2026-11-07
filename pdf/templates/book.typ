// Zúme Training guidebook — Typst book template
// Driven by book.json produced by the Python assembler.

#let book = json("book.json")

#set document(
  title: book.title + " — " + book.subtitle,
  author: "Zúme Project",
)
#set page(
  paper: "us-letter",
  margin: (top: 0.85in, bottom: 0.85in, left: 0.75in, right: 0.75in),
  numbering: none,
)
#set text(font: "Liberation Sans", size: 11pt, lang: book.lang)
#set par(justify: true, leading: 0.65em)
#show heading: it => block(breakable: false, sticky: true, above: 1.1em, below: 0.55em, it)

#let accent = rgb("#1f4e79")
#let muted = rgb("#555555")

#let section-label(label, duration: none) = {
  block(breakable: false, sticky: true, spacing: 0.85em)[
    #text(weight: "bold", size: 13pt, fill: accent, tracking: 0.06em)[#upper(label)]
    #if duration != none [
      #h(0.4em)
      #text(size: 10pt, fill: muted)[(#duration)]
    ]
  ]
}

#let keep-block(body) = block(breakable: false, sticky: true, width: 100%, body)

#let qr-figure(path, caption) = {
  if path == none or path == "" { return }
  keep-block[
    #align(center)[
      #box(width: 1.35in)[
        #image(path, width: 100%)
      ]
      #v(0.15em)
      #text(size: 8.5pt, fill: muted)[#caption]
    ]
  ]
}

#let bullets(items) = {
  if items == none or items.len() == 0 { return }
  for item in items [
    #block(sticky: true, spacing: 0.35em)[
      #grid(
        columns: (0.9em, 1fr),
        gutter: 0.25em,
        [•],
        [#item],
      )
    ]
  ]
}

// ---------- Cover ----------
#page(numbering: none, margin: 0.9in)[
  #align(center + horizon)[
    #text(size: 42pt, weight: "bold", fill: accent)[#book.title]
    #v(0.6em)
    #text(size: 20pt, fill: muted)[#book.subtitle]
    #v(1.4em)
    #line(length: 40%, stroke: 1pt + accent)
    #v(1.4em)
    #text(size: 14pt)[Training Guidebook]
    #v(2.5em)
    #text(size: 11pt, fill: muted)[#book.version_label]
    #v(0.4em)
    #text(size: 10pt, fill: muted)[Generated from live zume6 content]
  ]
]

#set page(numbering: "1", footer: context {
  let n = counter(page).get().first()
  align(center, text(size: 9pt, fill: muted)[#n])
})
#counter(page).update(1)

// ---------- Sessions ----------
#for session in book.sessions [
  #pagebreak(weak: false)

  #keep-block[
    #text(size: 22pt, weight: "bold", fill: accent)[#session.title]
  ]
  #v(0.4em)

  #for block-data in session.blocks [
    #let kind = block-data.at("kind")

    #if kind == "checkin" [
      #section-label(block-data.label, duration: block-data.at("duration", default: none))
      #keep-block[
        #grid(
          columns: (1fr, 1.5in),
          gutter: 0.6em,
          [
            #block-data.instruction \
            #v(0.35em)
            #text(size: 10pt)[#block-data.url_hint *#block-data.code*]
          ],
          qr-figure(block-data.at("qr", default: none), "Check-in"),
        )
      ]
    ] else if kind == "pray" [
      #section-label(block-data.label, duration: block-data.at("duration", default: none))
      #for p in block-data.at("paragraphs", default: ()) [
        #block(sticky: true)[#p]
        #v(0.25em)
      ]
    ] else if kind == "look_back" [
      #section-label(block-data.label, duration: block-data.at("duration", default: none))
      #for p in block-data.at("paragraphs", default: ()) [
        #block(sticky: true)[#p]
        #v(0.25em)
      ]
    ] else if kind == "overview" [
      #section-label("OVERVIEW", duration: block-data.at("duration", default: none))
      #if block-data.at("concepts_intro", default: "") != "" [
        #block(sticky: true)[#block-data.concepts_intro]
        #v(0.2em)
        #bullets(block-data.at("concepts", default: ()))
      ]
      #if block-data.at("tools_intro", default: "") != "" [
        #v(0.35em)
        #block(sticky: true)[#block-data.tools_intro]
        #v(0.2em)
        #bullets(block-data.at("tools", default: ()))
      ]
    ] else if kind == "read" [
      #section-label(block-data.label, duration: block-data.at("duration", default: none))
      #keep-block[
        #grid(
          columns: (1fr, 1.45in),
          gutter: 0.55em,
          [
            #text(weight: "bold", size: 12.5pt)[#block-data.title]
          ],
          qr-figure(block-data.at("qr", default: none), block-data.at("qr_caption", default: "Video")),
        )
      ]
      #v(0.2em)
      #for p in block-data.at("paragraphs", default: ()) [
        #par[#p]
        #v(0.35em)
      ]
    ] else if kind == "discuss" [
      #section-label(block-data.label, duration: block-data.at("duration", default: none))
      #if block-data.at("intro", default: "") != "" [
        #block(sticky: true)[#block-data.intro]
        #v(0.25em)
      ]
      #bullets(block-data.at("questions", default: ()))
    ] else if kind == "activity" [
      #section-label(block-data.label, duration: block-data.at("duration", default: none))
      #keep-block[
        #grid(
          columns: (1fr, 1.45in),
          gutter: 0.55em,
          [
            #text(weight: "bold", size: 12.5pt)[#block-data.title]
            #v(0.25em)
            #bullets(block-data.at("instructions", default: ()))
          ],
          qr-figure(block-data.at("qr", default: none), block-data.at("qr_caption", default: "Activity")),
        )
      ]
      #for p in block-data.at("paragraphs", default: ()) [
        #par[#p]
        #v(0.3em)
      ]
      #if block-data.at("worksheet", default: none) == "listof100" [
        #v(0.4em)
        #keep-block[
          #text(weight: "bold")[List of 100]
          #v(0.2em)
          #text(size: 9.5pt, fill: muted)[Write names below. Mark Disciple / Unbeliever / Unknown.]
        ]
        #let count = block-data.at("worksheet_count", default: 100)
        #for i in range(1, count + 1) [
          #block(breakable: false, sticky: true, spacing: 0.22em, width: 100%)[
            #grid(
              columns: (1.6em, 1fr),
              gutter: 0.3em,
              text(size: 9pt)[#i],
              [
                #box(width: 100%, stroke: (bottom: 0.4pt + luma(160)), inset: (bottom: 0.55em))[]
                #text(size: 7.5pt, fill: muted)[☐ Disciple   ☐ Unbeliever   ☐ Unknown]
              ],
            )
          ]
        ]
      ]
    ] else if kind == "center" [
      #if block-data.at("title", default: none) != none [
        #keep-block[
          #text(weight: "bold", size: 13pt, fill: accent)[#block-data.title]
        ]
        #v(0.25em)
      ]
      #for p in block-data.at("paragraphs", default: ()) [
        #par[#p]
        #v(0.3em)
      ]
    ] else if kind == "image_note" [
      #keep-block[
        #text(weight: "bold", size: 12.5pt)[#block-data.title]
      ]
      #for p in block-data.at("paragraphs", default: ()) [
        #text(style: "italic", fill: muted)[#p]
      ]
      #if block-data.at("qr", default: none) != none [
        #qr-figure(block-data.qr, block-data.at("qr_caption", default: ""))
      ]
    ] else if kind == "obey" [
      #section-label(block-data.label)
      #bullets(block-data.at("challenges", default: ()))
    ] else if kind == "congratulations" [
      #v(1em)
      #keep-block[
        #align(center)[
          #text(size: 16pt, weight: "bold", fill: accent)[#block-data.label]
          #v(0.6em)
          #for p in block-data.at("paragraphs", default: ()) [
            #par[#p]
            #v(0.3em)
          ]
          #v(0.5em)
          #qr-figure(block-data.at("qr", default: none), "Join the community")
        ]
      ]
    ]
  ]
]
