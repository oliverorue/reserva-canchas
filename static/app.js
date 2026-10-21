document.addEventListener("DOMContentLoaded", () => {
  const dateInput = document.getElementById("date");
  if (dateInput) {
    dateInput.addEventListener("change", () => {
      dateInput.form.submit();
    });
  }
});
