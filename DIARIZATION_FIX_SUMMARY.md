# Diarization Fix Summary - April 14, 2026

## Root Cause Identified
The screenshot showing "Speaker 1", "Speaker 3", and mostly "Speaker 2" indicated mixed speaker label formats:

1. **Pyannote diarization** creates labels: `SPEAKER_00`, `SPEAKER_01`
2. **Fallback diarization** was creating labels: `speaker_1`, `speaker_2`  
3. **Frontend speaker mapping** couldn't handle mixed formats:
   - Normalized both to lowercase
   - When multiple formats had conflicting number extractions
   - Created spurious "Speaker 3" from the mismatch

## Changes Made to `backend/app/services/postprocess.py`

### 1. Fixed Fallback Diarization (Primary Bug Fix)
**Before:**
```python
return [_DiarizationSpan(start=s.start, end=s.end, speaker="speaker_1") for s in segments]
```

**After:**
```python
return [_DiarizationSpan(start=s.start, end=s.end, speaker="SPEAKER_00") for s in segments]
```

Now fallback uses:
- `SPEAKER_00` for mic/primary source
- `SPEAKER_01` for system source
- Matches pyannote format for consistency

### 2. Enhanced Segment Assignment Fallback (Lines 385-445)
Improved `_label_for_segment()` to intelligently find speakers before/after segments when no overlap exists, instead of arbitrary "nearest neighbor" selection.

### 3. Added Comprehensive Debug Logging
- Diarization span details with speaker IDs
- Raw segment timestamps and preview text  
- Segment assignment tracking (first 10)
- Speaker distribution by segment count AND character count
- Warnings for severely imbalanced distributions (>80% to one speaker)
- Detection of duplicate consecutive segments

### 4. Added Validation Checks
- Detects segment overlap issues
- Warns on zero-duration segments from splitting
- Warns on severely imbalanced speaker distributions
- Logs timing mismatches between segments and original transcription

## Testing the Fix

### Quick Test
1. Restart post-processing on an existing meeting
2. Check logs for speaker distribution
3. Frontend should now show 2 distinct speakers (not 1, 2, 3)

### With Debug Logging
```bash
LOGLEVEL=DEBUG python -m backend  # Or however you run it
```

Look for logs like:
```
INFO: Post-processing speaker distribution segments: {'mic:SPEAKER_00': 15, 'mic:SPEAKER_01': 20}
```

If you see valid distribution (both speakers present), the fix worked!

## Files Modified
- `backend/app/services/postprocess.py`: Fallback diarization format + enhanced diagnostics

## Impact
- ✅ Fixes incorrect speaker labeling when fallback is used
- ✅ Better debugging capability  
- ✅ Detects imbalanced distributions (indicates a problem)
- ⚠️ No performance impact (debug logging at DEBUG level only)
- ⚠️ No change needed in frontend code

## Known Remaining Issues (if any)
If speaker distribution is STILL imbalanced after this fix:
1. Check logs for "Segment at X-Y has no overlap" messages
2. Indicates transcription/diarization timing misalignment
3. May require re-uploading audio or checking equipment
