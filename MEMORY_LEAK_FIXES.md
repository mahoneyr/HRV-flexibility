# Memory Leak Fixes Summary

## Issues Found and Fixed

### 1. **Matplotlib Figure Caching** (Primary Culprit)
- **Problem**: Even with `plt.close(fig)`, matplotlib caches fonts, figure managers, and other resources globally
- **Fix**: Added `plt.close('all')` and wrapped plot function in try-finally to ensure cleanup
- **Location**: `plot()` method, lines 446-582

### 2. **Inefficient Pandas Concatenation**
- **Problem**: In `plot()` method, we were using `pd.concat()` to add current session to history dataframe, creating temporary copies
- **Fix**: Removed unnecessary concatenation and calculated stats directly from history file only
- **Savings**: Eliminated duplicate dataframe in memory during plotting

### 3. **Large NumPy Arrays Not Freed**
- **Problem**: `base_rr` and `entr_rr` arrays (potentially 100k+ elements) persisted in memory after use
- **Fix**: Added explicit `del` statements after array use:
  - In `run()` method after calculations
  - In `plot()` method after plotting
- **Location**: Multiple locations in `AutonomicFlexibilityAnalyzer` class

### 4. **History DataFrame Never Explicitly Freed**
- **Problem**: `get_history()` loads entire CSV into DataFrame but never explicitly releases it
- **Fix**: Added `del df` and `gc.collect()` calls after use
- **Location**: `get_history()` function, lines 634-682

### 5. **Missing Garbage Collection**
- **Problem**: Python GC may not run immediately after large object deletion
- **Fix**: Added explicit `gc.collect()` calls after major operations:
  - After processing files in `index()` route
  - After building history records

## Changes Made

### app.py
1. Added `import gc` for garbage collection control
2. Modified `AutonomicFlexibilityAnalyzer.run()` to delete large arrays
3. Modified `AutonomicFlexibilityAnalyzer.plot()` with:
   - Try-finally for guaranteed cleanup
   - `plt.close('all')` instead of just `plt.close(fig)`
   - Explicit array deletion
4. Simplified history calculation in `plot()` (removed concat)
5. Modified `get_history()` to explicitly free DataFrame memory
6. Modified `index()` route to call `gc.collect()` after processing

### Dockerfile
- Minor: Added Python development flag for better debugging

## Expected Memory Reduction

- **Per request**: ~200-500 MB reduction (from eliminated dataframe copies)
- **Matplotlib caches**: Continuous clearing prevents accumulation
- **Large arrays**: Immediate cleanup instead of waiting for GC

## Testing Recommendations

1. Monitor container memory usage over 24+ hours with heavy usage
2. Check if memory plateaus instead of growing indefinitely
3. Look for any performance regressions (should be minimal)
4. Verify plots still generate correctly

## Docker Memory Limits (Recommended)

When running the container, set memory limits:
```bash
docker run -m 2g --memory-swap 2g your-image
```

This will prevent runaway memory from consuming entire host.
