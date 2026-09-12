from fastapi import FastAPI
app=FastAPI(title='Microgrid Energy Optimizer API')
@app.get('/')
def root(): return {'project':'Microgrid Energy Mix Optimizer','status':'running'}
