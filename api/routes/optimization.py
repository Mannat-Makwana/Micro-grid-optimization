from fastapi import APIRouter
router=APIRouter(prefix='/optimization',tags=['optimization'])
@router.get('/health')
def health():return {'status':'ready','engine':'MILP'}
