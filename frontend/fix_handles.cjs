const fs = require('fs');
let content = fs.readFileSync('src/builder/MeuMisterioNode.tsx', 'utf8');

// Replace handle dimensions
content = content.replace(/!w-\[22px\] !h-\[22px\]/g, '!w-[16px] !h-[16px]');
content = content.replace(/!w-\[20px\] !h-\[20px\]/g, '!w-[16px] !h-[16px]');
content = content.replace(/!w-\[18px\] !h-\[18px\]/g, '!w-[16px] !h-[16px]');

// Replace SVG dimensions inside handles
content = content.replace(/width=\"8\" height=\"10\" viewBox=\"0 0 8 10\"/g, 'width=\"6\" height=\"8\" viewBox=\"0 0 8 10\"');

fs.writeFileSync('src/builder/MeuMisterioNode.tsx', content);
