document.getElementById("download-cv").addEventListener("click", () => {
  const element = document.body;
  html2pdf().set({
    margin: 0.3,
    filename: 'Majid_Khoshrou_CV.pdf',
    html2canvas: { scale: 2 },
    jsPDF: { unit: 'in', format: 'a4', orientation: 'portrait' }
  }).from(element).save();
});
