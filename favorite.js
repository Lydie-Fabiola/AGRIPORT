// Get elements
const productsTab = document.getElementById("productsTab");
const farmersTab = document.getElementById("farmersTab");
const productsContent = document.getElementById("productsContent");
const farmersContent = document.getElementById("farmersContent");

// Tab click event handlers
productsTab.addEventListener("click", () => {
  productsTab.classList.add("active");
  farmersTab.classList.remove("active");
  
  productsContent.classList.add("active");
  farmersContent.classList.remove("active");
});

farmersTab.addEventListener("click", () => {
  farmersTab.classList.add("active");
  productsTab.classList.remove("active");
  
  farmersContent.classList.add("active");
  productsContent.classList.remove("active");
});
