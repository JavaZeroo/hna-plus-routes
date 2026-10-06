import React from 'react';
import {createRoot} from 'react-dom/client';
import {DashboardContent} from './DashboardContent.jsx';
import './site.css';
createRoot(document.getElementById('root')).render(<main><header><span className='eyebrow'>公开班表 · 航线探索</span><h1>海航 PLUS · 全国航线地图</h1><p>筛选候选航班，探索 199 元权益的出行方向</p></header><DashboardContent/></main>);
