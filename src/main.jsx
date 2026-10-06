import React from 'react';
import {createRoot} from 'react-dom/client';
import {DashboardContent} from './DashboardContent.jsx';
import './site.css';
createRoot(document.getElementById('root')).render(<main><header><span className='eyebrow'>官方班表 · 来源可追溯</span><h1>海航 PLUS · 全国航线地图</h1><p>按官方计划筛选起飞时间，查看航线与数据覆盖范围</p></header><DashboardContent/></main>);
