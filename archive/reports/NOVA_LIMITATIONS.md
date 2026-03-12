# Amazon Nova Embedding Limitations

## 100MB Video Size Limit

### The Issue

Amazon Nova multimodal embeddings have a **100MB maximum video size limit** for both sync and async APIs.

This is documented AWS behavior:
> "The maximum S3 object size is 100 MB. Try again with a smaller S3 object."

### Impact on Demo

**Videos That Work** ✅
- **MSR-VTT**: Most videos are 10-50MB (typical YouTube clips)
- **ActivityNet**: Usually 20-80MB
- **YouCook2**: Cooking instruction clips, typically 15-40MB
- **WebVid**: Web video clips, mostly under 100MB

**Videos That Don't Work** ❌
- **Blender Foundation videos**: 300-700MB each
  - Big Buck Bunny: ~560MB
  - Sintel: ~650MB
  - Elephants Dream: ~410MB
  - Tears of Steel: ~740MB

### Comparison with Marengo

| Feature | Marengo 2.7 | Amazon Nova |
|---------|-------------|-------------|
| **Max Video Size (Sync)** | 5MB | 100MB |
| **Max Video Size (Async)** | No limit | 100MB |
| **Best For** | Any size video | Videos <100MB |
| **Workaround** | Use async for >5MB | Split large videos into clips |

### Recommended Approach

#### For Demo Purposes:
1. **Use Marengo for large videos** (Blender Foundation content)
2. **Use Nova for dataset videos** (MSR-VTT, ActivityNet, WebVid)
3. **Showcase both approaches** with appropriate content

#### For Production:
1. **Pre-filter videos** by size before Nova processing
2. **Use Marengo** if you need to handle large videos (>100MB)
3. **Split large videos** into <100MB clips if using Nova
4. **Check video size** before submitting to avoid validation errors

### Implementation

Our implementation now includes:
- ✅ Async invocation for both models (production pattern)
- ✅ Automatic polling and S3 retrieval
- ✅ Format auto-detection
- ✅ Graceful error handling for over-limit videos

### Test Commands

**Nova with MSR-VTT** (works - videos <100MB):
```bash
conda run -n s3vector python scripts/run_dataset_stress_test.py \
  --dataset msr-vtt-100 \
  --model nova \
  --nova-dimension 1024 \
  --s3-bucket s3vector-test-datasets \
  --max-videos 20
```

**Marengo with Blender** (works - no size limit):
```bash
conda run -n s3vector python scripts/run_dataset_stress_test.py \
  --dataset blender \
  --model marengo \
  --vector-types visual-text \
  --s3-bucket s3vector-test-datasets
```

### Future Considerations

If AWS increases the Nova limit or adds chunking support, our async implementation is already ready to support it with minimal changes.

For now, the demo showcases:
- **Nova**: Unified single-vector approach (best for smaller videos)
- **Marengo**: Multi-vector task-specific approach (works with any size)

This actually demonstrates a real architectural trade-off that users need to consider!
