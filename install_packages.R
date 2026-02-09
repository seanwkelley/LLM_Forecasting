# Install required R packages for the wargame simulation

# List of required packages
required_packages <- c(
  "httr",        # HTTP requests for OpenRouter API
  "jsonlite",    # JSON parsing and writing
  "ggplot2",     # Visualization
  "dplyr",       # Data manipulation
  "tidyr",       # Data tidying
  "igraph",      # Network analysis and visualization
  "uuid"         # Generate unique identifiers
)

# Function to check and install packages
install_if_missing <- function(packages) {
  new_packages <- packages[!(packages %in% installed.packages()[,"Package"])]

  if (length(new_packages) > 0) {
    cat(sprintf("Installing %d missing packages...\n", length(new_packages)))
    install.packages(new_packages, dependencies = TRUE)
    cat("Installation complete!\n")
  } else {
    cat("All required packages are already installed.\n")
  }
}

# Install missing packages
cat("Checking required packages for wargame simulation...\n")
install_if_missing(required_packages)

# Verify installation
cat("\nVerifying installations...\n")
all_installed <- TRUE
for (pkg in required_packages) {
  if (require(pkg, character.only = TRUE, quietly = TRUE)) {
    cat(sprintf("  ✓ %s\n", pkg))
  } else {
    cat(sprintf("  ✗ %s - FAILED\n", pkg))
    all_installed <- FALSE
  }
}

if (all_installed) {
  cat("\n✓ All packages successfully installed and loaded!\n")
  cat("\nNext steps:\n")
  cat("1. Set your OpenRouter API key:\n")
  cat("   Sys.setenv(OPENROUTER_API_KEY = 'your-key-here')\n")
  cat("2. Run the simulation:\n")
  cat("   source('src/simulation.R')\n")
  cat("   state <- start_simulation()\n")
} else {
  cat("\n✗ Some packages failed to install. Please check error messages above.\n")
}
