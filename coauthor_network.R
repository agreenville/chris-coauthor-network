# ============================================================
#  Co-authorship Network Visualizer
#  Works in RStudio — run the whole script or source it
# ============================================================
#
#  INPUT OPTIONS
#  ─────────────
#  1. CSV  : columns  year | title | authors
#            authors must be semicolon-separated, e.g.:
#            "Smith JA; Jones BL; Brown KC"
#
#  2. BibTeX (.bib): exported from Zotero, Mendeley,
#            Web of Science, Google Scholar, etc.
#
#  OUTPUT
#  ──────
#  • Interactive HTML  (visNetwork)  → opens in RStudio Viewer
#  • Static PNG/PDF    (ggraph)      → for papers / CV / slides
#
#  INSTALL PACKAGES (run once)
#  ────────────────────────────
#  install.packages(c("tidyverse", "igraph", "visNetwork",
#                     "ggraph", "tidygraph", "bib2df",
#                     "RColorBrewer", "htmlwidgets"))
# ============================================================

library(tidyverse)
library(igraph)
library(visNetwork)
library(ggraph)
library(tidygraph)
library(htmlwidgets)

# ── Optional: BibTeX parsing ─────────────────────────────────
# library(bib2df)   # uncomment if using .bib input


# ============================================================
#  1.  SET YOUR INPUT FILE HERE
# ============================================================

input_file  <- "sample_papers.csv"   # ← change to your file path
focus_author <- "Smith Ja"           # ← your name (or NULL)
output_html  <- "coauthor_network.html"
output_png   <- "coauthor_network.png"


# ============================================================
#  2.  PARSERS
# ============================================================

parse_csv <- function(filepath) {
  df <- read_csv(filepath, show_col_types = FALSE)

  # Flexible column matching
  names(df) <- tolower(trimws(names(df)))
  author_col <- names(df)[str_detect(names(df), "author")][1]
  title_col  <- names(df)[str_detect(names(df), "title")][1]
  year_col   <- names(df)[str_detect(names(df), "year")][1]

  df %>%
    rename(authors = all_of(author_col),
           title   = any_of(c(title_col)),
           year    = any_of(c(year_col))) %>%
    mutate(authors = str_split(authors, ";")) %>%
    mutate(authors = map(authors, ~ str_trim(.x))) %>%
    mutate(authors = map(authors, ~ .x[nchar(.x) > 0]))
}


parse_bib <- function(filepath) {
  # Requires: library(bib2df)
  if (!requireNamespace("bib2df", quietly = TRUE))
    stop("Install bib2df:  install.packages('bib2df')")
  library(bib2df)

  bib <- bib2df(filepath)

  bib %>%
    filter(!is.na(AUTHOR)) %>%
    mutate(
      title   = coalesce(TITLE, "Untitled"),
      year    = as.character(YEAR),
      # bib2df returns AUTHOR as a list of "Last, First" strings
      authors = map(AUTHOR, function(a) {
        map_chr(a, normalise_name_bib)
      })
    ) %>%
    select(title, year, authors)
}


# BibTeX "Last, First Middle" → "Last FI"
normalise_name_bib <- function(name) {
  name <- str_trim(name)
  if (str_detect(name, ",")) {
    parts    <- str_split_fixed(name, ",", 2)
    last     <- str_trim(parts[1])
    first_parts <- str_trim(str_split(str_trim(parts[2]), "\\s+")[[1]])
    initials <- paste0(str_to_upper(str_sub(first_parts, 1, 1)), ".", collapse = "")
    paste(last, initials)
  } else {
    str_to_title(name)
  }
}


# ============================================================
#  3.  BUILD THE NETWORK
# ============================================================

build_network <- function(papers_df) {

  # Expand to one row per author per paper
  author_paper <- papers_df %>%
    select(title, year, authors) %>%
    unnest(authors) %>%
    rename(author = authors)

  # Node table: author + paper count
  nodes <- author_paper %>%
    count(author, name = "paper_count") %>%
    arrange(desc(paper_count)) %>%
    mutate(id = row_number())

  # Edge table: all co-author pairs per paper
  edges <- author_paper %>%
    inner_join(author_paper, by = "title", suffix = c("_a", "_b"),
               relationship = "many-to-many") %>%
    filter(author_a < author_b) %>%          # keep unique pairs only
    count(author_a, author_b, name = "weight") %>%
    # Collect shared paper titles for tooltips
    left_join(
      author_paper %>%
        inner_join(author_paper, by = "title", suffix = c("_a", "_b"),
                   relationship = "many-to-many") %>%
        filter(author_a < author_b) %>%
        group_by(author_a, author_b) %>%
        summarise(shared_papers = paste(unique(title), collapse = "<br>• "),
                  .groups = "drop"),
      by = c("author_a", "author_b")
    )

  # Join node ids
  edges <- edges %>%
    left_join(nodes %>% select(id, author), by = c("author_a" = "author")) %>%
    rename(from = id) %>%
    left_join(nodes %>% select(id, author), by = c("author_b" = "author")) %>%
    rename(to = id)

  list(nodes = nodes, edges = edges, author_paper = author_paper)
}


# ============================================================
#  4.  INTERACTIVE PLOT  (visNetwork → HTML)
# ============================================================

plot_interactive <- function(net, focus_author = NULL,
                             output_file = "coauthor_network.html") {

  nodes      <- net$nodes
  edges      <- net$edges
  max_papers <- max(nodes$paper_count)
  max_weight <- max(edges$weight)

  # Node size scaled to paper count
  nodes <- nodes %>%
    mutate(
      value = 10 + 35 * (paper_count / max_papers),
      label = author,
      title = paste0(
        "<b>", author, "</b><br>",
        "Papers: ", paper_count, "<br>",
        "Collaborators: ", map_int(author, ~ {
          sum(edges$author_a == .x | edges$author_b == .x)
        })
      ),
      color.background = case_when(
        !is.null(focus_author) & author == focus_author ~ "#f97316",
        paper_count >= max_papers * 0.7                 ~ "#58a6ff",
        TRUE                                             ~ "#3fb950"
      ),
      color.border      = "#0d1117",
      color.highlight.background = "#f97316",
      font.color        = "#e6edf3",
      font.size         = 13
    )

  # Edge width + tooltip
  edges_vis <- edges %>%
    mutate(
      width = 1 + 7 * (weight / max_weight),
      title = paste0(
        "<b>", author_a, "</b> ↔ <b>", author_b, "</b><br>",
        "Shared papers: ", weight, "<br><br>• ", shared_papers
      ),
      color = "#58a6ff"
    ) %>%
    select(from, to, width, title, color, weight)

  p <- visNetwork(nodes, edges_vis,
                  background = "#0d1117",
                  main = list(text = "Co-authorship Network",
                              style = "color:#e6edf3;font-size:18px;")) %>%
    visOptions(
      highlightNearest = list(enabled = TRUE, degree = 1, hover = TRUE),
      nodesIdSelection = list(enabled = TRUE,
                              style = "background:#161b22;color:#e6edf3;")
    ) %>%
    visPhysics(
      solver = "forceAtlas2Based",
      forceAtlas2Based = list(
        gravitationalConstant = -60,
        centralGravity        = 0.01,
        springLength          = 120,
        springConstant        = 0.08
      ),
      stabilization = list(iterations = 200)
    ) %>%
    visInteraction(navigationButtons = TRUE, keyboard = TRUE) %>%
    visLayout(randomSeed = 42)

  # Save + open in RStudio Viewer
  saveWidget(p, file = output_file, selfcontained = TRUE)
  message("✅  Interactive HTML saved → ", output_file)
  p   # also prints in Viewer pane
}


# ============================================================
#  5.  STATIC PLOT  (ggraph → PNG / PDF)
# ============================================================

plot_static <- function(net, focus_author = NULL,
                        output_file = "coauthor_network.png",
                        width = 14, height = 10) {

  nodes <- net$nodes
  edges <- net$edges

  # Build tidygraph object
  tg <- tbl_graph(
    nodes = nodes %>% mutate(name = author),
    edges = edges %>% select(from, to, weight),
    directed = FALSE
  )

  max_w <- max(edges$weight)

  p <- ggraph(tg, layout = "fr") +
    geom_edge_link(
      aes(width = weight, alpha = weight),
      colour = "#58a6ff",
      lineend = "round"
    ) +
    scale_edge_width(range = c(0.4, 4), guide = "none") +
    scale_edge_alpha(range = c(0.2, 0.9), guide = "none") +
    geom_node_point(
      aes(size = paper_count,
          colour = if (!is.null(focus_author))
            ifelse(name == focus_author, "focus", "other")
            else "other"),
      alpha = 0.9
    ) +
    scale_size(range = c(3, 14), name = "Papers") +
    scale_colour_manual(values = c(focus = "#f97316", other = "#3fb950"),
                        guide = "none") +
    geom_node_text(
      aes(label = name),
      repel      = TRUE,
      size       = 3,
      colour     = "white",
      bg.colour  = "#0d111799",
      bg.r       = 0.15
    ) +
    labs(
      title    = "Co-authorship Network",
      subtitle = paste0(nrow(nodes), " authors · ",
                        nrow(edges), " collaborations"),
      size     = "Papers"
    ) +
    theme_graph(background = "#0d1117",
                text_colour = "white",
                title_size  = 16) +
    theme(
      plot.title    = element_text(colour = "white", size = 16),
      plot.subtitle = element_text(colour = "#8b949e", size = 11),
      legend.background = element_rect(fill = "#161b22", colour = NA),
      legend.text   = element_text(colour = "white"),
      legend.title  = element_text(colour = "white")
    )

  ggsave(output_file, p, width = width, height = height,
         dpi = 180, bg = "#0d1117")
  message("📊  Static PNG saved → ", output_file)
  p
}


# ============================================================
#  6.  SUMMARY STATS  (printed to console)
# ============================================================

print_stats <- function(net) {
  nodes <- net$nodes
  edges <- net$edges

  cat("\n── Top authors by paper count ─────────────────────────\n")
  nodes %>%
    arrange(desc(paper_count)) %>%
    slice_head(n = 10) %>%
    mutate(line = sprintf("  %-35s %d papers", author, paper_count)) %>%
    pull(line) %>%
    cat(sep = "\n")

  cat("\n\n── Strongest collaborations ───────────────────────────\n")
  edges %>%
    arrange(desc(weight)) %>%
    slice_head(n = 10) %>%
    mutate(line = sprintf("  %-28s ↔  %-28s  %d papers",
                          author_a, author_b, weight)) %>%
    pull(line) %>%
    cat(sep = "\n")
  cat("\n")
}


# ============================================================
#  7.  RUN EVERYTHING
# ============================================================

# ── Parse ────────────────────────────────────────────────────
ext <- tools::file_ext(input_file)

message("📄 Parsing ", input_file, " …")
papers <- if (ext == "csv") parse_csv(input_file) else parse_bib(input_file)
message("   Found ", nrow(papers), " papers")

# ── Build ────────────────────────────────────────────────────
net <- build_network(papers)
print_stats(net)

# ── Visualise ────────────────────────────────────────────────
# Interactive HTML — opens in RStudio Viewer pane
interactive_plot <- plot_interactive(net,
                                     focus_author = focus_author,
                                     output_file  = output_html)

# Static PNG — for publications / slides
static_plot <- plot_static(net,
                           focus_author = focus_author,
                           output_file  = output_png)
