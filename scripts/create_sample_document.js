const { Document, Packer, Paragraph, TextRun, ImageRun, AlignmentType, HeadingLevel } = require('docx');
const fs = require('fs');
const path = require('path');

// Create a simple sample document with company letterhead
const doc = new Document({
  styles: {
    default: {
      document: {
        run: { font: "Arial", size: 24 } // 12pt default
      }
    },
    paragraphStyles: [
      {
        id: "Heading1",
        name: "Heading 1",
        basedOn: "Normal",
        next: "Normal",
        run: { size: 32, bold: true, color: "2E75B6", font: "Arial" },
        paragraph: { spacing: { before: 240, after: 120 } }
      },
      {
        id: "Heading2",
        name: "Heading 2",
        basedOn: "Normal",
        next: "Normal",
        run: { size: 28, bold: true, color: "2E75B6", font: "Arial" },
        paragraph: { spacing: { before: 180, after: 100 } }
      }
    ]
  },
  sections: [{
    properties: {
      page: {
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    children: [
      // Company Header/Logo Area
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 200 },
        children: [
          new TextRun({
            text: "ACME CORPORATION",
            bold: true,
            size: 36,
            color: "2E75B6",
            font: "Arial"
          })
        ]
      }),
      
      // Company Address
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 120 },
        children: [
          new TextRun({
            text: "123 Business Street, Suite 100",
            size: 20,
            color: "595959"
          })
        ]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 120 },
        children: [
          new TextRun({
            text: "New York, NY 10001, United States",
            size: 20,
            color: "595959"
          })
        ]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 400 },
        children: [
          new TextRun({
            text: "Phone: (555) 123-4567 | Email: info@acmecorp.com",
            size: 20,
            color: "595959"
          })
        ]
      }),
      
      // Document Title
      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        alignment: AlignmentType.CENTER,
        spacing: { before: 200, after: 200 },
        children: [
          new TextRun("Business Proposal")
        ]
      }),
      
      // Date
      new Paragraph({
        alignment: AlignmentType.RIGHT,
        spacing: { after: 240 },
        children: [
          new TextRun({
            text: "Date: October 27, 2025",
            italics: true
          })
        ]
      }),
      
      // Introduction
      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        children: [new TextRun("Introduction")]
      }),
      
      new Paragraph({
        spacing: { after: 200 },
        children: [
          new TextRun(
            "Thank you for considering our services. This proposal outlines our comprehensive solution designed to meet your business needs and exceed your expectations."
          )
        ]
      }),
      
      new Paragraph({
        spacing: { after: 240 },
        children: [
          new TextRun(
            "We are committed to delivering exceptional quality and value to all our clients. Our team of experts has over 20 years of combined experience in the industry."
          )
        ]
      }),
      
      // Services Section
      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        children: [new TextRun("Our Services")]
      }),
      
      new Paragraph({
        spacing: { after: 120 },
        children: [
          new TextRun({
            text: "Consulting Services: ",
            bold: true
          }),
          new TextRun(
            "We provide expert guidance to help your business grow and thrive in today's competitive market."
          )
        ]
      }),
      
      new Paragraph({
        spacing: { after: 120 },
        children: [
          new TextRun({
            text: "Implementation Support: ",
            bold: true
          }),
          new TextRun(
            "Our team will work closely with you to ensure smooth implementation of all solutions."
          )
        ]
      }),
      
      new Paragraph({
        spacing: { after: 240 },
        children: [
          new TextRun({
            text: "Training Programs: ",
            bold: true
          }),
          new TextRun(
            "Comprehensive training for your staff to maximize the value of our solutions."
          )
        ]
      }),
      
      // Pricing Section
      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        children: [new TextRun("Investment")]
      }),
      
      new Paragraph({
        spacing: { after: 200 },
        children: [
          new TextRun(
            "Our pricing is competitive and transparent. We offer flexible payment plans to accommodate your budget requirements."
          )
        ]
      }),
      
      new Paragraph({
        spacing: { after: 120 },
        children: [
          new TextRun("• Basic Package: $5,000 - Ideal for small businesses")
        ]
      }),
      
      new Paragraph({
        spacing: { after: 120 },
        children: [
          new TextRun("• Professional Package: $10,000 - Perfect for growing companies")
        ]
      }),
      
      new Paragraph({
        spacing: { after: 240 },
        children: [
          new TextRun("• Enterprise Package: $25,000 - Complete solution for large organizations")
        ]
      }),
      
      // Conclusion
      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        children: [new TextRun("Next Steps")]
      }),
      
      new Paragraph({
        spacing: { after: 200 },
        children: [
          new TextRun(
            "We would be delighted to discuss this proposal with you in more detail. Please contact us at your earliest convenience to schedule a meeting."
          )
        ]
      }),
      
      new Paragraph({
        spacing: { after: 400 },
        children: [
          new TextRun(
            "We look forward to the opportunity to work with you and help your business achieve its goals."
          )
        ]
      }),
      
      // Signature
      new Paragraph({
        spacing: { before: 400 },
        children: [
          new TextRun({
            text: "Best regards,",
            italics: true
          })
        ]
      }),
      
      new Paragraph({
        spacing: { before: 120 },
        children: [
          new TextRun({
            text: "John Smith",
            bold: true,
            size: 26
          })
        ]
      }),
      
      new Paragraph({
        children: [
          new TextRun({
            text: "Director of Business Development",
            italics: true
          })
        ]
      }),
      
      new Paragraph({
        children: [
          new TextRun("ACME Corporation")
        ]
      })
    ]
  }]
});

// Save the document
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("sample_document.docx", buffer);
  console.log("Sample document created: sample_document.docx");
  console.log("\nThis document contains:");
  console.log("✓ Company name and branding");
  console.log("✓ Address information");
  console.log("✓ Formatted headings");
  console.log("✓ Multiple sections with content");
  console.log("✓ Various text formatting (bold, italic, colors)");
  console.log("\nYou can now translate this document using:");
  console.log("  python document_translator.py sample_document.docx translated_document.docx es");
});
