// Zúme Training guidebook — reference two-column layout.
// LTR: left rail = section labels, timing, QR; right = reading content.
// RTL (Arabic): columns mirror — content left, QR/rail on the trailing (right) side.
//
// QR fix: unbreakable top-aligned grid keeps label+QR with enough body-column
// text so the QR never sits beside an empty band (orphaned at page bottom).

#let book = json("book.json")

#let accent = rgb("#1f4e79")
#let rule-blue = rgb("#7eb6d9")
#let muted = rgb("#444444")

#let is-rtl = book.at("direction", default: "ltr") == "rtl"

#let sidebar-w = 1.65in
// Balanced gutters around the blue bar: space beside the bar (QR/labels) ≈
// space beside the bar (body text). Content inset is half of the prior 0.42in;
// the freed space moves into col-gutter so content isn’t over-indented and
// rail items aren’t flush against the stroke.
#let col-gutter = 0.21in
#let content-inset = 0.21in
#let rail-pad = sidebar-w + col-gutter
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
  // Mirror outer/inner side margins for RTL chrome.
  margin: if is-rtl {
    (top: 0.75in, bottom: 1in, left: 0.55in, right: 0.45in)
  } else {
    (top: 0.75in, bottom: 1in, left: 0.45in, right: 0.55in)
  },
  numbering: none,
)
// Font stack: Latin body + script fallbacks (Arabic / CJK) swapped in by prepare_build_dir.
// typst_lang is ISO 639 (required); book.lang stays the zume site code (e.g. zhtw).
// Text dir handles Arabic shaping; column order is explicit below (grids stay LTR-ordered).
#set text(
  font: ("Liberation Sans",),
  size: 9.5pt,
  fill: black,
  lang: book.at("typst_lang", default: book.lang),
  region: {
    let r = book.at("typst_region", default: none)
    if r == none or r == "" { none } else { r }
  },
  dir: if is-rtl { rtl } else { ltr },
)
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

// Labels hug the blue bar: right edge of rail (LTR) / left edge of rail (RTL).
#let sidebar-label-only(label, duration: none) = {
  if label == none or label == "" { return }
  align(if is-rtl { left } else { right })[
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
    stroke: if is-rtl { (right: 1pt + rule-blue) } else { (left: 1pt + rule-blue) },
    inset: if is-rtl {
      (right: content-inset, top: 0.1em, bottom: 0.25em)
    } else {
      (left: content-inset, top: 0.1em, bottom: 0.25em)
    },
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

/// Script/activity body item: plain string or `{image, alt}` from book.json.
#let content-item(item) = {
  if type(item) == str {
    para-block[#item]
  } else if type(item) == dictionary {
    let src = item.at("image", default: none)
    if src != none and src != "" {
      block(width: 100%, breakable: false)[
        #align(center)[
          #image(src, width: 95%)
        ]
      ]
      v(para-gap)
    } else if item.at("text", default: none) != none {
      para-block[#item.text]
    }
  }
}

#let paras(items) = {
  if items == none { return }
  for item in items {
    content-item(item)
  }
}

#let bullets(items) = {
  if items == none or items.len() == 0 { return }
  for item in items [
    #block(breakable: false, sticky: true, width: 100%)[
      // Lock grid to LTR column order so parent dir:rtl does not double-flip
      // the marker. Explicitly place • on the reading-start side.
      #{
        set text(dir: ltr)
        if is-rtl {
          grid(
            columns: (1fr, 0.85em),
            gutter: 0.2em,
            align(top + right, {
              set text(dir: rtl)
              item
            }),
            align(top + right)[•],
          )
        } else {
          grid(
            columns: (0.85em, 1fr),
            gutter: 0.2em,
            align(top + left)[•],
            align(top + left, item),
          )
        }
      }
    ]
    #v(0.65em)
  ]
}

/// Two-col section grid with explicit LTR/RTL column order (not auto-flipped).
/// Layout uses LTR grid flow so columns don't double-flip under document RTL;
/// each cell re-applies text dir for Arabic shaping.
#let section-columns(sidebar, body) = {
  let text-dir = if is-rtl { rtl } else { ltr }
  let rail = {
    set text(dir: text-dir)
    sidebar
  }
  let body-cell = {
    set text(dir: text-dir)
    body
  }
  // Force LTR grid flow so we own placement: LTR = [rail | body], RTL = [body | rail].
  set text(dir: ltr)
  if is-rtl {
    grid(
      columns: (1fr, sidebar-w),
      column-gutter: col-gutter,
      align(top, body-cell),
      align(top, rail),
    )
  } else {
    grid(
      columns: (sidebar-w, 1fr),
      column-gutter: col-gutter,
      align(top, rail),
      align(top, body-cell),
    )
  }
}

/// Short sections without rail QR.
#let guidebook-section(label, duration: none, body) = {
  dashed-rule()
  block(breakable: false, sticky: true, width: 100%, below: 0.35em)[
    #section-columns(
      block(width: 100%)[#sidebar-label-only(label, duration: duration)],
      content-panel(body),
    )
  ]
}

/// READ/ACTIVITY with rail QR.
/// Unbreakable opener grid: [label+QR | title + enough paragraphs to fill QR height] (LTR),
/// mirrored for RTL. Remaining paragraphs continue in the body column (rail-padded).
/// This prevents an orphan QR at the bottom of a page with an empty body band.
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

  // Labels + QR hug the blue vertical bar (Chris tweak #1).
  // Must be width:100% so align hugs the bar instead of shrink-wrapping outward.
  let sidebar = block(width: 100%)[
    #sidebar-label-only(label, duration: duration)
    #if qr != none and qr != "" [
      #v(0.65em)
      #align(if is-rtl { left } else { right })[
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
    #section-columns(
      sidebar,
      content-panel[
        #if title != none [
          #para-block[#text(weight: "bold", size: 9.5pt)[#title]]
        ]
        #if lead-extra != none [#lead-extra]
        #for p in lead {
          content-item(p)
        }
      ],
    )
  ]

  if rest.len() > 0 or rest-extra != none [
    #block(
      breakable: true,
      width: 100%,
      inset: if is-rtl { (right: rail-pad) } else { (left: rail-pad) },
      above: 0em,
    )[
      #content-panel[
        #for p in rest {
          content-item(p)
        }
        #if rest-extra != none [#rest-extra]
      ]
    ]
  ]
}

// ---------- Cover ----------
// Version string is drawn from book.version_label (cover PNG has the old
// baked-in label whitened out so Typst owns the v6.0 text).
#page(margin: 0pt, numbering: none)[
  #block(width: 100%, height: 100%)[
    #image("cover-10.png", width: 100%, height: 100%, fit: "cover")
    #place(
      bottom + center,
      dy: -0.48in,
      text(size: 9.5pt, fill: rgb("#787878"))[#book.version_label],
    )
  ]
]

#page(numbering: none)[]

#set page(numbering: "1", footer: context {
  let n = counter(page).get().first()
  align(center, text(size: 10pt, fill: black)[#n])
})
#counter(page).update(3)

// ---------- Sessions ----------
// Each session opener starts on an odd (recto) page for duplex printing.
// If the previous session ended on an odd page, Typst inserts a blank even page.
#for session in book.sessions [
  #pagebreak(weak: false, to: "odd")

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
      // Presenter order in the body column: instruction, QR, then the URL and code.
      // The rail keeps only the section label and duration.
      #dashed-rule()
      #block(breakable: false, sticky: true, width: 100%, below: 0.35em)[
        #section-columns(
          block(width: 100%)[
            #sidebar-label-only(
              block-data.label,
              duration: block-data.at("duration", default: none),
            )
          ],
          content-panel[
            #para-block[#block-data.instruction]
            #if block-data.at("qr", default: none) != none and block-data.qr != "" [
              #align(if is-rtl { right } else { left })[
                #image(block-data.qr, width: qr-size)
              ]
              #v(para-gap)
            ]
            #para-block[#block-data.url_hint #text(weight: "bold")[#block-data.code]]
          ],
        )
      ]
    ] else if kind == "break" [
      #guidebook-section(block-data.label)[
        #paras(block-data.at("paragraphs", default: ()))
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
        block-data.at("label", default: "OVERVIEW"),
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
        let ws-title = block-data.at("worksheet_title", default: "List of 100")
        let ws-hint = block-data.at(
          "worksheet_hint",
          default: "Write names below. Mark Disciple / Unbeliever / Unknown.",
        )
        let marks = block-data.at("worksheet_marks", default: ("Disciple", "Unbeliever", "Unknown"))
        let m0 = if marks.len() > 0 { marks.at(0) } else { "Disciple" }
        let m1 = if marks.len() > 1 { marks.at(1) } else { "Unbeliever" }
        let m2 = if marks.len() > 2 { marks.at(2) } else { "Unknown" }
        {
          v(0.35em)
          text(weight: "bold")[#ws-title]
          v(0.3em)
          text(size: 8.5pt, fill: muted)[#ws-hint]
          let count = block-data.at("worksheet_count", default: 100)
          for i in range(1, count + 1) [
            #block(breakable: false, sticky: true, below: 0.3em, width: 100%)[
              #grid(
                columns: (1.5em, 1fr),
                gutter: 0.25em,
                text(size: 9pt)[#i],
                [
                  #box(width: 100%, stroke: (bottom: 0.4pt + luma(160)), inset: (bottom: 0.5em))[]
                  #text(size: 7.5pt, fill: muted)[☐ #m0   ☐ #m1   ☐ #m2]
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
      #block(
        inset: if is-rtl { (right: rail-pad) } else { (left: rail-pad) },
        width: 100%,
      )[
        #content-panel[
          #if block-data.at("title", default: none) != none [
            #para-block[#text(weight: "bold", size: 11pt)[#block-data.title]]
          ]
          #paras(block-data.at("paragraphs", default: ()))
        ]
      ]
    ] else if kind == "image_note" [
      #let qr = block-data.at("qr", default: none)
      #let diagram = block-data.at("image", default: none)
      #let diagram-body = {
        if diagram != none and diagram != "" {
          (
            (image: diagram, alt: block-data.at("image_alt", default: "")),
            ..block-data.at("paragraphs", default: ()),
          )
        } else {
          block-data.at("paragraphs", default: ())
        }
      }
      #if qr != none [
        #guidebook-section-qr(
          "",
          qr: qr,
          title: block-data.title,
          paragraphs: diagram-body,
          beside-min: 3,
        )
      ] else [
        #dashed-rule()
        #block(
          inset: if is-rtl { (right: rail-pad) } else { (left: rail-pad) },
          width: 100%,
        )[
          #content-panel[
            #para-block[#text(weight: "bold")[#block-data.title]]
            #if diagram != none and diagram != "" [
              #content-item((image: diagram, alt: block-data.at("image_alt", default: "")))
            ]
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
