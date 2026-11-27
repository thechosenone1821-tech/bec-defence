"""End-to-end smoke test for VIGIL through the FastAPI API."""
import cv2
import numpy as np
import io
import zipfile

from fastapi.testclient import TestClient
from vigil_app.main import app

c = TestClient(app)

# Build a synthetic 480x360 image with a face-like oval + dark eye/mouth patches
img = np.full((360, 480, 3), 70, dtype=np.uint8)
cv2.ellipse(img, (240, 180), (90, 120), 0, 0, 360, (200, 170, 150), -1)
cv2.ellipse(img, (210, 160), (16, 8), 0, 0, 360, (40, 30, 30), -1)
cv2.ellipse(img, (270, 160), (16, 8), 0, 0, 360, (40, 30, 30), -1)
cv2.ellipse(img, (240, 230), (40, 14), 0, 0, 360, (90, 50, 50), -1)
ok, buf = cv2.imencode('.png', img)
assert ok

# 1. Upload
r = c.post('/api/sessions/upload',
           files={'file': ('synthetic_face.png', buf.tobytes(), 'image/png')},
           data={'auto_resize': 'true'})
print('1. POST /api/sessions/upload ->', r.status_code)
data = r.json()
sid = data['session_id']
print('   session_id:', sid)
print('   working_dimensions:', data['working_dimensions'])
print('   regions detected:', len(data['regions']))
for reg in data['regions'][:5]:
    print('     - {} {:14s} conf={:.2f} source={}'.format(
        reg['region_id'], reg['category'], reg['confidence'], reg['detector_source']))
print('   perception_metadata counts:', data['perception_metadata']['counts_by_category'])
print('   model_status.mode:', data['perception_metadata']['model_status']['system_mode'])

# 2. Execute VIGIL with gaussian_noise
r2 = c.post('/api/vigil/execute', json={
    'session_id': sid,
    'config': {
        'policy_id': 'policy_strict',
        'method': 'gaussian_noise',
        'noise_sigma': 25.0,
        'random_seed': 42,
        'apply_noise_to': 'selected_regions',
        'mask_dilation_px': 0,
    },
    'run_evaluation': True,
})
print()
print('2. POST /api/vigil/execute ->', r2.status_code)
exec_data = r2.json()
print('   processing_time_ms:', exec_data['processing_time_ms'])
audit = exec_data['audit_report']
print('   audit.overall_audit_status:', audit['overall_audit_status'])
print('   audit.active_protected_regions:', audit['active_protected_regions'])
print('   audit.target_mask_pixel_ratio:', round(audit['target_mask_pixel_ratio'], 4))
print('   audit.modified_pixels_within_target_ratio:', round(audit['modified_pixels_within_target_ratio'], 4))
print('   audit.unintended_background_modification_ratio:', round(audit['unintended_background_modification_ratio'], 6))
print('   audit.checks:', audit['checks'])
print('   audit.system_mode:', audit['system_mode'])
eval_rep = exec_data['evaluation_report']
print('   eval.full_image_ssim:', eval_rep['full_image_ssim'])
print('   eval.full_image_psnr_db:', eval_rep['full_image_psnr_db'])
print('   eval.protected_region_ssim:', eval_rep['protected_region_ssim'])
print('   eval.protected_region_mean_l1_diff:', eval_rep['protected_region_mean_l1_diff'])
print('   eval.controlled_transforms keys:', [ct['transform_key'] for ct in eval_rep['controlled_transforms']])
print('   eval.detector_retention categories:', [d['category'] for d in eval_rep['detector_retention']])
print('   transformed_png_url starts with data:image/png:',
      exec_data['transformed_png_url'].startswith('data:image/png;base64,'))

# 3. Export PNG / JSON / ZIP
png_r = c.get('/api/export/{}/image.png'.format(sid))
print()
print('3. GET /api/export/.../image.png ->', png_r.status_code,
      '| bytes:', len(png_r.content), '| content-type:', png_r.headers['content-type'])
json_r = c.get('/api/export/{}/audit.json'.format(sid))
print('   GET /api/export/.../audit.json ->', json_r.status_code, '| bytes:', len(json_r.content))
zip_r = c.get('/api/export/{}/bundle.zip'.format(sid))
print('   GET /api/export/.../bundle.zip ->', zip_r.status_code, '| bytes:', len(zip_r.content))

zf = zipfile.ZipFile(io.BytesIO(zip_r.content))
print('   ZIP contents:', zf.namelist())

# 4. PNG verify endpoint on the exported PNG
verify_r = c.post('/api/security/verify-png',
                  files={'file': ('vigil.png', png_r.content, 'image/png')})
print()
print('4. POST /api/security/verify-png ->', verify_r.status_code)
vj = verify_r.json()
print('   is_clean_png:', vj['is_clean_png'])
print('   chunks_present:', vj['chunks_present'])
print('   forbidden_metadata_chunks_found:', vj['forbidden_metadata_chunks_found'])
print('   all_crc32_valid:', vj['all_crc32_valid'])

# 5. Purge
del_r = c.delete('/api/sessions/{}'.format(sid))
print()
print('5. DELETE /api/sessions/{sid} ->', del_r.status_code, '| purged:', del_r.json()['purged'])

# 6. Overview after
ov = c.get('/api/overview').json()
print()
print('6. GET /api/overview after purge -> active_sessions_in_ram:',
      ov['sessions']['active_sessions_in_ram'])
print('   recent_sessions count:', len(ov['sessions']['recent_sessions']))
print('   process_rss_mb:', ov['hardware_profile']['process_rss_mb'])
