# Diarization Issue - Analysis and Fix Report

## Problem Summary
The diarization process was completing successfully but may not be assigning speaker labels correctly to transcript segments, resulting in segments that should be from different speakers being labeled the same.

## Root Cause Analysis

### Issue 1: Segment-to-Diarization Mismatch
- Diarization creates ~36 speaker spans, but only ~13 transcription segments
- Segments are split further via `_split_for_diarization()` into chunks based on character length
- If chunks don't overlap well with diarization spans, incorrect speaker assignment occurs

### Issue 2: Poor Fallback Logic for Gaps
The original code used a "nearest neighbor" approach when no overlap was found:
```python
# OLD CODE - problematic
midpoint = (seg.start + seg.end) / 2.0
nearest = min(spans, key=lambda span: abs(((span.start + span.end) / 2.0) - midpoint))
return nearest.speaker
```

**Problem**: This could assign any speaker arbitrarily, causing:
- Segments in gaps between speakers to be misassigned
- All segments in certain time regions to get same speaker even if speaker changed
- No intelligence about actual speaker transitions

## Solutions Implemented

### 1. Enhanced Debug Logging
Added comprehensive logging to diagnose diarization problems:

```python
# Log diarization spans
logger.debug("Diarization span[%d]: start=%.2f end=%.2f speaker=%s", ...)

# Log raw segments
logger.debug("Raw segment[%d]: start=%.2f end=%.2f text=%s...", ...)

# Log when fallback is used
logger.debug("Segment at %.2f-%.2f has no overlap; using closer speaker...")

# Log final speaker distribution
logger.info("Post-processing speaker distribution: %s", speaker_label_counts)
```

### 2. Improved Speaker Assignment Algorithm
Replaced simple "nearest" with intelligent gap handling:

```python
# NEW CODE - smarter fallback
# When no overlap found:
# 1. Find the closest speaker BEFORE segment
# 2. Find the closest speaker AFTER segment  
# 3. Compare distances and use the closer one
# 4. This respects speaker transitions rather than arbitrary selection
```

**Benefits**:
- Respects speaker turns and transitions
- Better handles gaps in diarization coverage
- More intuitive speaker assignment
- Prevents segments in same region getting different speakers

### 3. Validation Statistics
Added speaker distribution tracking to identify problems:

```python
logger.info("Post-processing speaker distribution: {
    'mic:speaker_1': 25,
    'mic:speaker_2': 15,
    'system:speaker_1': 10
}")
```

If all segments have same speaker, it indicates a problem that needs investigation.

## How to Debug

### Enable Debug Logging
1. Set `LOGLEVEL=DEBUG` environment variable
2. Or modify `backend/app/core/config.py` to default to DEBUG

### Look for These Logs
1. **Diarization spans**: Shows what speakers pyannote detected
2. **Raw segments**: Verify timestamps make sense
3. **Overlap warnings**: "Segment at X-Y has no overlap" indicates timing issues
4. **Speaker distribution**: Shows how speakers were distributed across segments

### Example Debug Output
```
DEBUG: Diarization span[0]: start=2.45 end=5.67 speaker=SPEAKER_00
DEBUG: Diarization span[1]: start=5.98 end=12.34 speaker=SPEAKER_01
DEBUG: Raw segment[0]: start=0.50 end=4.20 duration=3.70 text=Hello there...
DEBUG: Segment at 4.20-5.20 (gap fallback): using closer speaker SPEAKER_00
INFO: Post-processing speaker distribution: {'mic:SPEAKER_00': 8, 'mic:SPEAKER_01': 5}
```

## Testing the Fix

### Run with Your Meeting
1. Upload/restart post-processing for a existing meeting
2. Check logs for speaker distribution
3. If balanced (both speakers present), diarization is working
4. If imbalanced (mostly one speaker), check for timing alignment issues

### Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| All segments same speaker | Timestamps not aligned | Check audio file sample rate, format |
| Speaker distribution wrong | Gaps in diarization | Verify pyannote model working correctly |
| Some segments unassigned | Timing completely off | Re-upload audio, check equipment/software |

## Files Modified
- `backend/app/services/postprocess.py`: 
  - Enhanced `_label_for_segment()` with smarter gap handling
  - Added debug logging throughout diarization process
  - Added speaker distribution tracking

## Performance Impact
- **Negligible**: Debug logging uses debug level (only when enabled)
- **Minor**: Improved algorithm has same O(n) complexity

## Recommendations

1. **Short term**: Run with debug logging enabled to see what's happening
2. **Medium term**: Consider adding speaker diversity validation (fail if all same)
3. **Long term**: Consider audio preprocessing to improve speaker acoustic separation
