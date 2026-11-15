// SVG paths ported from the prototype's build.py (viewBox 0 0 24 24)
export const ICONS = {
 "cal": "<path fill=\"currentColor\" d=\"M7 2h2v2h6V2h2v2h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2V2zM5 9v11h14V9H5zm2 2h4v4H7v-4z\"/>",
 "map": "<path fill=\"currentColor\" d=\"M15 5.1 9 3 3 5v16l6-2.1 6 2.1 6-2V3l-6 2.1zM15 19l-6-2.1V5l6 2.1V19z\"/>",
 "list": "<path fill=\"currentColor\" d=\"M3 5h4v4H3zm6 1h12v2H9zM3 10h4v4H3zm6 1h12v2H9zM3 15h4v4H3zm6 1h12v2H9z\"/>",
 "bell": "<path fill=\"currentColor\" d=\"M12 22a2 2 0 0 0 2-2h-4a2 2 0 0 0 2 2zm6-6V11a6 6 0 0 0-5-5.9V4a1 1 0 0 0-2 0v1.1A6 6 0 0 0 6 11v5l-2 2v1h16v-1l-2-2z\"/>",
 "help": "<path fill=\"currentColor\" d=\"M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm1 17h-2v-2h2v2zm2.1-7.7-.9.9c-.7.7-1.2 1.3-1.2 2.8h-2v-.5c0-1.1.5-2.1 1.2-2.8l1.2-1.3A2 2 0 1 0 10 9H8a4 4 0 1 1 7.1 2.3z\"/>",
 "calc": "<path fill=\"currentColor\" d=\"M6 2h12a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zm1 3v4h10V5H7zm0 7v2h2v-2H7zm4 0v2h2v-2h-2zm4 0v6h2v-6h-2zm-8 4v2h2v-2H7zm4 0v2h2v-2h-2z\"/>",
 "leaf": "<path fill=\"currentColor\" d=\"M17 8C8 10 5.9 16.2 3.8 21.3l1.9.7 1-2.3c.5.2 1 .3 1.3.3C19 20 22 3 22 3c-1 2-8 2.3-13 3.3S2 11.5 2 13.5s1.8 3.8 1.8 3.8C7 8 17 8 17 8z\"/>",
 "warn": "<path fill=\"currentColor\" d=\"M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z\"/>",
 "drop": "<path fill=\"currentColor\" d=\"M12 2s-7 7.6-7 12.5A7 7 0 0 0 19 14.5C19 9.6 12 2 12 2z\"/>",
 "rain": "<path fill=\"currentColor\" d=\"M18 9a6 6 0 0 0-11.6-1.5A4.5 4.5 0 0 0 7 16.5h11A3.75 3.75 0 0 0 18 9zM8 18.2l-1 3 1.6.6 1-3zm4 0-1 3 1.6.6 1-3zm4 0-1 3 1.6.6 1-3z\"/>",
 "frost": "<path fill=\"currentColor\" d=\"M11 2h2v4.2l2.5-1.5 1 1.7L13 8.5V11h2.5l2.1-3.6 1.7 1-1.5 2.6H22v2h-4.2l1.5 2.6-1.7 1-2.1-3.6H13v2.5l3.5 2.1-1 1.7-2.5-1.5V22h-2v-4.2l-2.5 1.5-1-1.7L11 15.5V13H8.5l-2.1 3.6-1.7-1L6.2 13H2v-2h4.2L4.7 8.4l1.7-1L8.5 11H11V8.5L7.5 6.4l1-1.7L11 6.2z\"/>",
 "layers": "<path fill=\"currentColor\" d=\"M12 2 1 8l11 6 11-6-11-6zm0 14.5L3.4 11.8 1 13.1l11 6 11-6-2.4-1.3L12 16.5z\"/>",
 "erosion": "<path fill=\"currentColor\" d=\"M2 6h20v2c-3 0-4 1.5-6 1.5S13 8 10 8 6 9.5 2 9.5V6zm0 6c4 0 5-1.5 8-1.5s4 1.5 6 1.5 3-1 6-1v3c-3 0-4 1-6 1s-3-1.5-6-1.5S6 15 2 15v-3zm0 6c4 0 5-1 8-1s4 1 6 1 3-.5 6-.5V22H2v-4z\"/>",
 "straw": "<path fill=\"currentColor\" d=\"M3 20h18v2H3zM5 19l3-9 1.5.5-2.6 8.5zm4 0 1-11 1.6.2-.9 10.8zm4 0 .3-12h1.6l-.2 12zm4 0-1.3-9.5 1.6-.2 1.3 9.7z\"/>",
 "nitro": "<path fill=\"currentColor\" d=\"M12 2a3 3 0 0 1 3 3c0 1.3-.8 2.4-2 2.8V11h4a3 3 0 0 1 3 3v2.2a3 3 0 1 1-2 0V14a1 1 0 0 0-1-1h-4v3.2a3 3 0 1 1-2 0V13H7a1 1 0 0 0-1 1v2.2a3 3 0 1 1-2 0V14a3 3 0 0 1 3-3h4V7.8A3 3 0 0 1 12 2z\"/>",
 "bare": "<path fill=\"currentColor\" d=\"M2 14h20v8H2zm3 2v2h2v-2zm5 1v2h2v-2zm5-1v2h2v-2zM11 3h2v5h3l-4 4-4-4h3z\"/>",
 "coin": "<path fill=\"currentColor\" d=\"M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm1 15.9V20h-2v-2.1c-1.7-.4-3-1.5-3.1-3.2h2c.1.9 1 1.6 2.6 1.6 1.7 0 2-.8 2-1.3 0-.7-.4-1.3-2.3-1.8-2.1-.5-3.6-1.4-3.6-3.2 0-1.5 1.2-2.6 2.9-3V4.9h2V7c1.6.4 2.6 1.6 2.6 3.1h-2c0-.9-.6-1.5-2-1.5s-2 .6-2 1.3c0 .6.5 1 2.3 1.5s3.6 1.2 3.6 3.4c0 1.6-1.2 2.7-3.1 3.1z\"/>",
 "tool": "<path fill=\"currentColor\" d=\"m22.7 19-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z\"/>",
 "check": "<path fill=\"currentColor\" d=\"M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z\"/>",
 "x": "<path fill=\"currentColor\" d=\"M19 6.4 17.6 5 12 10.6 6.4 5 5 6.4 10.6 12 5 17.6 6.4 19 12 13.4 17.6 19 19 17.6 13.4 12z\"/>",
 "info": "<path fill=\"currentColor\" d=\"M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z\"/>",
 "up": "<path fill=\"currentColor\" d=\"m7 14 5-5 5 5z\"/>",
 "down": "<path fill=\"currentColor\" d=\"m7 10 5 5 5-5z\"/>",
 "pencil": "<path fill=\"currentColor\" d=\"M3 17.2V21h3.8L17.8 9.9l-3.7-3.7L3 17.2zM20.7 7a1 1 0 0 0 0-1.4l-2.3-2.3a1 1 0 0 0-1.4 0l-1.8 1.8 3.7 3.7L20.7 7z\"/>",
 "slope": "<path fill=\"currentColor\" d=\"M2 20 22 6v14z\"/>",
 "grip": "<path fill=\"currentColor\" d=\"M8 5h2v2H8zm6 0h2v2h-2zM8 11h2v2H8zm6 0h2v2h-2zm-6 6h2v2H8zm6 0h2v2h-2z\"/>"
}

export const SCALE_IC = {
 "field": "<path fill=\"currentColor\" d=\"M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z\"/>",
 "area": "<path fill=\"currentColor\" d=\"M19.4 10A7.5 7.5 0 0 0 5.3 8.1 6 6 0 0 0 6 20h13a5 5 0 0 0 .4-10z\"/>",
 "book": "<path fill=\"currentColor\" d=\"M18 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12V2zM6 4h5v8l-2.5-1.5L6 12V4z\"/>",
 "est": "<path fill=\"currentColor\" d=\"M3 9c2-2 4-2 6 0s4 2 6 0 4-2 6 0v3c-2-2-4-2-6 0s-4 2-6 0-4-2-6 0V9zm0 6c2-2 4-2 6 0s4 2 6 0 4-2 6 0v3c-2-2-4-2-6 0s-4 2-6 0-4-2-6 0v-3z\"/>"
}

export const SCALE_TXT = { field: 'measured on your field', area: 'data for your area', book: 'crop knowledge', est: 'estimate' }
