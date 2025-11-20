import { describe, expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { createSpreadsheetWithList } from "@spreadsheet/../tests/helpers/list";
import { mountSpreadsheet } from "@spreadsheet/../tests/helpers/ui";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";

defineSpreadsheetModels();

async function openListSidePanel(listId) {
    await contains(".o-topbar-menu[data-id='data']").click();
    await contains(`.o-menu-item[data-name='item_list_${listId}']`).click();
}

describe("list side panel", () => {
    test("can remove an invalid sorting field", async () => {
        const orderBy = [{ name: "an_invalid_field", asc: true }];
        const { model } = await createSpreadsheetWithList({
            model: "partner",
            orderBy,
        });
        await mountSpreadsheet(model);
        const [listId] = model.getters.getListIds();
        expect(model.getters.getListDefinition(listId).orderBy).toEqual(orderBy);
        await openListSidePanel(listId);
        expect(".o_sorting_rule_column .fa-exclamation-triangle").toHaveCount(1);
        await contains(".o_sorting_rule_column .fa-times").click();
        expect(model.getters.getListDefinition(listId).orderBy).toEqual([]);
    });
});
