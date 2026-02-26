// Virtual file system fonts for pdfmake
// This file maps font file names to their base64 encoded content
// Add custom fonts here as needed

window.pdfMake = window.pdfMake || {};
window.pdfMake.vfs = {
    // Add custom fonts in base64 format here
    // Example:
    // "Roboto-Regular.ttf": "BASE64_ENCODED_FONT_DATA"
};

// Default empty fonts object for basic functionality
window.pdfMake.fonts = {
    Roboto: {
        normal: 'Roboto-Regular.ttf',
        bold: 'Roboto-Medium.ttf',
        italics: 'Roboto-Italic.ttf',
        bolditalics: 'Roboto-MediumItalic.ttf'
    }
};
