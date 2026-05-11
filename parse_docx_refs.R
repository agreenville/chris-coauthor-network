# ============================================================
#  parse_docx_refs.R
#  Add-on for coauthor_network.R
#
#  Reads a Word (.docx) reference list and extracts
#  authors + titles into the same format the network
#  script expects.
#
#  SUPPORTED CITATION STYLES
#  ──────────────────────────
#  ESA / Ecology  :  Smith JA, Jones BL, Brown KC. 2022. Title. Journal.
#  ESA long       :  Smith, J. A., B. L. Jones, and K. C. Brown. 2022. Title.
#  APA            :  Smith, J. A., Jones, B. L., & Brown, K. C. (2022). Title.
#  Numbered       :  1. Smith JA, Jones BL (2022) Title. Journal.
#  Vancouver      :  Smith JA, Jones BL, Brown KC. Title. Journal. 2022.
#
#  If your format isn't listed, run in DIAGNOSTIC MODE first —
#  it prints each reference so you can see what was parsed.
#
#  INSTALL (run once)
#  ──────────────────
#  install.packages(c("officer", "tidyverse"))
# ============================================================

library(officer)
library(tidyverse)


# ============================================================
#  MAIN FUNCTION
# ============================================================

parse_docx_refs <- function(filepath,
                            diagnostic = FALSE,
                            min_authors = 1) {
  # ── Read Word document ─────────────────────────────────────
  doc  <- read_docx(filepath)
  body <- docx_summary(doc)

  # Keep only paragraph text, drop tables/headers/empty lines
  paras <- body %>%
    filter(content_type == "paragraph",
           !is.na(text),
           nchar(trimws(text)) > 20) %>%
    pull(text) %>%
    str_trim()

  if (diagnostic) {
    cat("── DIAGNOSTIC: first 10 paragraphs ────────────────────\n")
    walk(head(paras, 10), ~ cat("  |", .x, "\n"))
    cat("\n")
  }

  # ── Detect and parse each reference ───────────────────────
  results <- map(paras, parse_one_reference) %>%
    keep(~ !is.null(.x))

  if (length(results) == 0)
    stop("No references could be parsed. Run with diagnostic = TRUE to inspect the raw text.")

  df <- bind_rows(results) %>%
    filter(map_int(authors, length) >= min_authors)

  if (diagnostic) {
    cat("── PARSED REFERENCES ───────────────────────────────────\n")
    walk2(df$title, df$authors, function(t, a) {
      cat("  Title  :", str_trunc(t, 60), "\n")
      cat("  Authors:", paste(a, collapse = " | "), "\n\n")
    })
  }

  message("   Parsed ", nrow(df), " references from ", basename(filepath))
  df
}


# ============================================================
#  PARSE ONE REFERENCE  (tries each format in order)
# ============================================================

parse_one_reference <- function(ref) {
  ref <- str_trim(ref)

  # Strip leading number:  "1." "1)" "[1]"
  ref <- str_remove(ref, "^\\[?\\d{1,3}[\\]\\)\\.]\\s*")

  # ── Try to find the year ───────────────────────────────────
  # Looks for (2022) or . 2022. or  2022;  or  2022:
  year_match <- str_match(ref,
    "(\\(?(19|20)\\d{2}[a-z]?\\)?)")

  year <- if (!is.na(year_match[1, 1])) {
    str_extract(year_match[1, 1], "(19|20)\\d{2}")
  } else { "?" }

  # ── Split at the year to isolate the author block ─────────
  #   Everything before the year = authors
  #   Everything after = title + journal
  split_pos <- str_locate(ref,
    "(\\(?(19|20)\\d{2}[a-z]?\\)?\\.?\\s)")

  if (is.na(split_pos[1, 1])) {
    # No year found — fall back: assume authors end at first "."
    # followed by a capital letter (title start)
    split_pos2 <- str_locate(ref, "\\.\\s+[A-Z]")
    if (is.na(split_pos2[1, 1])) return(NULL)
    author_block <- str_sub(ref, 1, split_pos2[1, 1] - 1)
    rest         <- str_sub(ref, split_pos2[1, 2])
  } else {
    author_block <- str_sub(ref, 1, split_pos[1, 1] - 1)
    rest         <- str_sub(ref, split_pos[1, 2])
  }

  author_block <- str_trim(author_block)
  rest         <- str_trim(rest)

  # ── Parse the author block ─────────────────────────────────
  authors <- parse_author_block(author_block)
  if (length(authors) == 0) return(NULL)

  # ── Title: first sentence of 'rest' ───────────────────────
  title <- str_extract(rest, "^[^.!?]+[.!?]") %>%
    str_remove("\\s*\\.\\s*$") %>%
    str_trim()
  if (is.na(title) || nchar(title) < 5) title <- str_trunc(rest, 80)

  list(year = year, title = title, authors = list(authors))
}


# ============================================================
#  AUTHOR BLOCK PARSER
#  Handles mixed separator styles within the author string
# ============================================================

parse_author_block <- function(block) {
  block <- str_trim(block)
  if (nchar(block) == 0) return(character(0))

  # Remove trailing punctuation
  block <- str_remove(block, "[,;\\s]+$")

  # ── Strategy A: semicolon-separated ───────────────────────
  if (str_detect(block, ";")) {
    authors <- str_split(block, ";")[[1]]
    return(map_chr(authors, normalise_author) %>% keep(~ nchar(.x) > 1))
  }

  # ── Strategy B: ESA long form ─────────────────────────────
  # "Smith, J. A., B. L. Jones, and K. C. Brown"
  # Clue: "and" or "&" before last author
  if (str_detect(block, "\\band\\b|\\b&\\b")) {
    # Replace "and" / "&" with comma for uniform splitting
    block2 <- str_replace_all(block, "(,?\\s+)(and|&)\\s+", ", ")
    authors <- str_split(block2, ",\\s+(?=[A-Z])")[[1]]
    if (length(authors) > 1)
      return(map_chr(authors, normalise_author) %>% keep(~ nchar(.x) > 1))
  }

  # ── Strategy C: "Last FI, Last FI, Last FI" ──────────────
  # Split on comma-space where next token looks like Last FI or FI Last
  authors <- str_split(block, ",\\s+(?=[A-Z][a-z]+\\s|[A-Z]{2,}\\s)")[[1]]
  if (length(authors) > 1)
    return(map_chr(authors, normalise_author) %>% keep(~ nchar(.x) > 1))

  # ── Strategy D: "Last, F. I., Last, F. I." ───────────────
  # APA: last name first, then initials with periods
  apa_pattern <- "(\\b[A-Z][a-z]+([-'][A-Z][a-z]+)*,\\s+[A-Z]\\.[^,]+)"
  apa_matches <- str_extract_all(block, apa_pattern)[[1]]
  if (length(apa_matches) > 0)
    return(map_chr(apa_matches, normalise_author) %>% keep(~ nchar(.x) > 1))

  # ── Fallback: treat whole block as one author ─────────────
  a <- normalise_author(block)
  if (nchar(a) > 1) return(a)
  character(0)
}


# ============================================================
#  NAME NORMALISER  → "Lastname FI" format
# ============================================================

normalise_author <- function(name) {
  name <- str_trim(name)
  name <- str_remove_all(name, "\\.$")       # trailing period
  name <- str_remove(name, "^(Dr|Prof|Mr|Mrs|Ms)\\.?\\s+")

  # Skip "et al"
  if (str_detect(tolower(name), "^et\\.?\\s*al")) return("")

  # "Last, First Middle"  or  "Last, F. I."
  if (str_detect(name, "^[A-Z][a-z].+,")) {
    parts    <- str_split_fixed(name, ",\\s*", 2)
    last     <- str_trim(parts[1])
    given    <- str_trim(parts[2])
    # Collapse given to initials
    initials <- str_extract_all(given, "\\b[A-Z]")[[1]] %>%
      paste(collapse = "")
    return(if (nchar(initials) > 0) paste(last, initials) else last)
  }

  # "First Last"  or  "Last FI"  (no comma)
  tokens <- str_split(name, "\\s+")[[1]]
  if (length(tokens) >= 2) {
    last_token <- tokens[length(tokens)]
    # If last token is all-caps initials, it's already "Last FI"
    if (str_detect(last_token, "^[A-Z]{1,3}$")) return(name)
    # If first token looks like initials, swap: "FI Last" → "Last FI"
    if (str_detect(tokens[1], "^[A-Z]{1,3}$")) {
      return(paste(last_token, tokens[1]))
    }
    # Otherwise title-case and return as-is
    return(str_to_title(name))
  }

  str_to_title(name)
}


# ============================================================
#  USAGE EXAMPLES
# ============================================================

# ── Basic usage ───────────────────────────────────────────────
# papers <- parse_docx_refs("my_publications.docx")

# ── See what the parser is doing ──────────────────────────────
# papers <- parse_docx_refs("my_publications.docx", diagnostic = TRUE)

# ── Then feed straight into the network builder ───────────────
# net <- build_network(papers)
# plot_interactive(net, focus_author = "Smith JA",
#                  output_file = "coauthor_network.html")

# ── Or combine with a CSV (e.g., older + newer papers) ────────
# old_papers <- parse_csv("old_papers.csv")
# new_papers <- parse_docx_refs("new_papers.docx")
# all_papers <- bind_rows(old_papers, new_papers)
# net        <- build_network(all_papers)


# ============================================================
#  QUICK SELF-TEST  (comment out if not needed)
# ============================================================

test_parse_author_block <- function() {
  tests <- list(
    list(input = "Smith JA, Jones BL, Brown KC",
         note  = "ESA short"),
    list(input = "Smith, J. A., B. L. Jones, and K. C. Brown",
         note  = "ESA long"),
    list(input = "Smith, J. A., Jones, B. L., & Brown, K. C.",
         note  = "APA"),
    list(input = "Smith JA, Jones BL",
         note  = "Two authors"),
    list(input = "Brown, K. C., Davis, M. R., et al.",
         note  = "et al.")
  )

  cat("── Author parsing self-test ────────────────────────────\n")
  for (t in tests) {
    result <- parse_author_block(t$input)
    cat(sprintf("  %-12s : %s\n  %-12s → %s\n\n",
                t$note, t$input, "", paste(result, collapse = " | ")))
  }
}

# Run the self-test

chris <- parse_docx_refs("Chris_pubs.docx")
