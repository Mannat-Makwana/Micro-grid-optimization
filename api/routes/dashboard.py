from fastapi import APIRouter
router=APIRouter(prefix='/dashboard',tags=['dashboard'])
@router.get('/health')
def health():return {'status':'ready'}
