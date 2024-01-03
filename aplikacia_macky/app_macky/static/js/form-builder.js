// static/js/form-builder.js

document.addEventListener('DOMContentLoaded', function() {
  const formFields = document.getElementById('form-fields');
  const addedAttributeIds = new Set(); // To track added attributes

  // Function to enable the "Add" button for a given attribute
  function enableAddButton(attributeId) {

    /*
    addButton = document.querySelector(`.add-attribute-btn[data-attribute-id="${attributeId}"]`);
    if (addButton) {
      addButton.removeAttribute('disabled');
    }
    */
    //document.querySelector('.add-attribute-btn').disabled = false;

    document.querySelectorAll('.add-attribute-btn').forEach(btn => {
      btn.addEventListener('click', function() {        
        alert(`attributeId: ${attributeId}, attributeName: ${attributeName}, attributeType: ${attributeType}, required: ${required}`);
        console.log(`attributeId: ${attributeId}, attributeName: ${attributeName}, attributeType: ${attributeType}, required: ${required}`);
  
        // Disable the button after adding the attribute
        //btn.disabled = false;
      });
    });
  }

  // Function to remove an attribute from the form preview
  function removeAttribute(row, attributeId) {
    row.remove();
    addedAttributeIds.delete(attributeId); // Unmark the attribute as added
    enableAddButton(attributeId); // Re-enable the "Add" button
  }

  // Function to move an attribute up
  function moveUp(row) {
    const previousRow = row.previousElementSibling;
    if (previousRow) {
      formFields.insertBefore(row, previousRow);
    }
  }

  // Function to move an attribute down
  function moveDown(row) {
    const nextRow = row.nextElementSibling;
    if (nextRow) {
      // Move the current row (row) below the next row (nextRow)
      formFields.insertBefore(row, nextRow.nextSibling);
    }
  }

  // Function to add an attribute to the form preview
  function addAttributeToForm(attributeId, attributeName, attributeType, required) {
    if (addedAttributeIds.has(attributeId)) {
      return; // Don't add the attribute if it's already added
    }

    const row = document.createElement('tr');
    row.setAttribute('data-attribute-id', attributeId);
    row.innerHTML = `
      <td>${attributeName}</td>
      <td>${attributeType}</td>
      <td>
        <div class="form-check">
          <input class="form-check-input" type="checkbox" id="attribute${attributeId}"
            name="attr_req_${attributeId}"
            value="${required}" ${required ? 'checked' : ''}>
        </div>
      </td>
      <td>
        <button type="button" class="btn btn-secondary move-up-btn">↑</button>
        <button type="button" class="btn btn-secondary move-down-btn">↓</button>
        <button type="button" class="btn btn-danger remove-attribute-btn">Remove</button>
        <input type="hidden" name="attribute_${attributeId}" value="${attributeId}">
      </td>
    `;


    bindRowEvents(row);


    formFields.appendChild(row);
    addedAttributeIds.add(attributeId);
  }

  // Bind event listeners to the move and remove buttons
  function bindRowEvents(row) {
    row.querySelector('.move-up-btn').addEventListener('click', () => moveUp(row));
    row.querySelector('.move-down-btn').addEventListener('click', () => moveDown(row));
    row.querySelector('.remove-attribute-btn').addEventListener('click', function() {
      removeAttribute(row, row.getAttribute('data-attribute-id'));
    });
  }

  // Attach event listeners to existing rows (for edit mode)
  document.querySelectorAll('#form-fields tr').forEach(bindRowEvents);

  // Event delegation to handle adding attributes
  document.querySelectorAll('.add-attribute-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const attributeRow = btn.closest('.attribute-row');
      const attributeId = attributeRow.getAttribute('data-attribute-id');
      const attributeName = attributeRow.getAttribute('data-attribute-name');
      const attributeType = attributeRow.getAttribute('data-attribute-type');
      addAttributeToForm(attributeId, attributeName, attributeType, true);
    });
  });
});
