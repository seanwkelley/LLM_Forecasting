# Troubleshooting Guide

## Common Issues and Solutions

### 1. Model Not Available Error

**Error:**
```
API call failed with status 404: model not found
```

**Solution:**
- Check that `qwen/qwen3-235b-a22b-2507` is available on OpenRouter
- Visit https://openrouter.ai/models to see available models
- If needed, update `config.R` with an alternative model:
  ```r
  AGENT_MODEL <- "qwen/qwen-2.5-72b-instruct"  # Alternative Qwen model
  # or
  AGENT_MODEL <- "meta-llama/llama-3.1-70b-instruct"  # Meta model
  ```

### 2. Moderation/Content Policy Errors (403)

**Error:**
```
API call failed with status 403: flagged for "illicit/violent"
```

**Solution:**
The code has been updated to avoid this. If you still see it:
1. Check you're using the latest version of the code
2. Verify you're NOT using Anthropic models (use Qwen or others)
3. The issue was the combination of Anthropic + Bedrock moderation

**Models without strict moderation:**
- `qwen/qwen3-235b-a22b-2507` ✅ (current default)
- `qwen/qwen-2.5-72b-instruct` ✅
- `meta-llama/llama-3.1-70b-instruct` ✅
- Most non-Anthropic models on OpenRouter ✅

### 3. API Key Issues

**Error:**
```
Error: OPENROUTER_API_KEY environment variable not set
```

**Solution:**
```r
# Set temporarily
Sys.setenv(OPENROUTER_API_KEY = "sk-or-v1-...")

# Set permanently (add to ~/.Renviron)
# On Windows: Create/edit %USERPROFILE%\.Renviron
# On Mac/Linux: Create/edit ~/.Renviron
# Add line:
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### 4. Missing Package Errors

**Error:**
```
Error in library(xxx): there is no package called 'xxx'
```

**Solution:**
```r
source("install_packages.R")
# or manually:
install.packages("httr")
install.packages("jsonlite")
install.packages("ggplot2")
install.packages("dplyr")
install.packages("tidyr")
install.packages("igraph")
install.packages("uuid")
```

### 5. Simulation Runs Slowly

**Symptoms:**
- Takes >30 minutes for 10 periods
- Long waits between agent responses

**Solutions:**
1. **Use a faster model:**
   ```r
   # In config.R, change to:
   AGENT_MODEL <- "qwen/qwen-2.5-7b-instruct"  # Smaller, faster
   ```

2. **Reduce simulation periods:**
   ```r
   state <- run_simulation(n_periods = 3)  # Instead of 10
   ```

3. **Check OpenRouter credits:**
   - Low credits can cause rate limiting
   - Visit https://openrouter.ai/credits

### 6. JSON Parsing Errors

**Error:**
```
Error in fromJSON(...): unexpected character
```

**Cause:** LLM didn't return properly formatted JSON for some responses

**Solution:**
This is rare. If it happens:
1. Check the full error message for which function failed
2. The aggregator uses regex parsing (not JSON), so it's more robust
3. Agent responses are stored as plain text, so no JSON parsing needed
4. If persistent, file an issue with the full error trace

### 7. Directory Permission Errors

**Error:**
```
Error in dir.create(...): cannot create directory
```

**Solution:**
```r
# Check write permissions in current directory
getwd()

# Change to a directory where you have write access
setwd("C:/Users/YourName/Documents")  # Windows
setwd("~/Documents")  # Mac/Linux

# Then run simulation
source("src/simulation.R")
state <- start_simulation()
```

### 8. Simulation Stops Unexpectedly

**Symptoms:**
- Simulation completes only 3-4 periods instead of 10
- "Government collapse highly likely - ending simulation" message

**Explanation:**
This is **NORMAL** behavior! The simulation has early termination logic:
```r
if (assessment$probability > 0.9) {
  cat("\n*** Government collapse highly likely - ending simulation ***\n")
  break
} else if (assessment$probability < 0.05) {
  cat("\n*** Government collapse highly unlikely - ending simulation ***\n")
  break
}
```

**To disable** (run all periods regardless):
Edit `src/simulation.R` and comment out the early termination check (around line 60).

### 9. Network Plot Errors

**Error:**
```
Error in plot.igraph(...): could not find function "plot"
```

**Solution:**
```r
library(igraph)
# Ensure igraph is loaded before plotting

# If still fails, reinstall:
remove.packages("igraph")
install.packages("igraph")
```

### 10. Memory Issues (Long Simulations)

**Symptoms:**
- R session crashes
- "Cannot allocate vector of size..." errors

**Solutions:**
1. **Reduce logging:**
   ```r
   # In config.R
   SAVE_FULL_TRANSCRIPTS <- FALSE
   ```

2. **Process in batches:**
   ```r
   # Run periods 1-5
   state <- run_simulation(n_periods = 5)

   # Then resume for 6-10
   state <- run_simulation(resume_from_period = 6, n_periods = 10)
   ```

3. **Increase R memory** (if using RStudio):
   - Tools → Global Options → General → Advanced
   - Increase memory limit

## Getting Help

### Before Asking for Help

1. Check this troubleshooting guide
2. Review `QUICKSTART.md` for setup steps
3. Check `FIXED_ISSUES.md` for recent fixes
4. Look at `example_usage.R` for code patterns

### Diagnostic Information to Provide

When reporting issues, include:
```r
# R version
R.version.string

# Package versions
packageVersion("httr")
packageVersion("jsonlite")

# Working directory
getwd()

# Model configuration
AGENT_MODEL
AGGREGATOR_MODEL

# Test API connection
source("config.R")
library(httr)
test_response <- POST(
  url = paste0(OPENROUTER_BASE_URL, "/chat/completions"),
  add_headers("Authorization" = paste("Bearer", OPENROUTER_API_KEY)),
  body = toJSON(list(
    model = AGENT_MODEL,
    messages = list(list(role = "user", content = "test"))
  ), auto_unbox = TRUE),
  encode = "json"
)
status_code(test_response)  # Should be 200
```

### Still Stuck?

- Check OpenRouter status: https://status.openrouter.ai/
- Review OpenRouter docs: https://openrouter.ai/docs
- Check model availability: https://openrouter.ai/models

## Performance Optimization Tips

### Fastest Configuration
```r
# In config.R:
AGENT_MODEL <- "qwen/qwen-2.5-7b-instruct"  # Fast model
N_PERIODS <- 3  # Fewer periods
SAVE_FULL_TRANSCRIPTS <- TRUE  # Keep this for analysis
SAVE_NETWORK_DATA <- FALSE  # Skip if not needed
```

### Most Detailed Configuration
```r
# In config.R:
AGENT_MODEL <- "qwen/qwen3-235b-a22b-2507"  # High quality
N_PERIODS <- 15  # More periods
SAVE_FULL_TRANSCRIPTS <- TRUE
SAVE_NETWORK_DATA <- TRUE
```

### Balanced Configuration (Default)
```r
AGENT_MODEL <- "qwen/qwen3-235b-a22b-2507"
N_PERIODS <- 10
SAVE_FULL_TRANSCRIPTS <- TRUE
SAVE_NETWORK_DATA <- TRUE
```

Expected runtime: ~10-20 minutes
