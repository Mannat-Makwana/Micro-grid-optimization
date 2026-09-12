from fastapi import APIRouter
router=APIRouter(prefix='/what-if',tags=['what-if'])
@router.get('/health')
def health():return {'status':'ready'}
