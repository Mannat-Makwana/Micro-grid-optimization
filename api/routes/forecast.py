from fastapi import APIRouter
router=APIRouter(prefix='/forecast',tags=['forecast'])
@router.get('/health')
def health():return {'status':'ready'}
