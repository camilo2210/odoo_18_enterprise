from freezegun import freeze_time

from odoo import Command, fields
from odoo.tests import tagged
from odoo.tools import date_utils

from odoo.addons.l10n_it_reports.tests.test_tax_report import TestItalianTaxReport


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItalianTaxReportXmlExport(TestItalianTaxReport):

    def _create_invoice_for_reported_period(self):
        """Helper method to create and post invoices in each month of the reported quarter. Depends on today's date (use freeze_time)."""
        invoices = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'partner_id': self.l10n_it_tax_report_partner.id,
            'date': date,
            'invoice_date': date,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Product A',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 5 * (10 ** i),
                    'quantity': 10,
                    'tax_ids': self.tax_4a,
                }),
            ],
        } for i, date in enumerate(list(date_utils.date_range(*date_utils.get_quarter(fields.Date.today()))))])
        invoices.action_post()

    def _get_file_content(self, forced_options=False):
        """Helper method returning the file data of the period's xml export. Allows for options overrides."""
        options = self._generate_options(self.report, fields.Date.today(), fields.Date.today())

        # Add the options coming from the export wizard
        options.update({
            "declarant_fiscal_code": (self.env.company.account_representative_id or self.env.company).l10n_it_codice_fiscale,
            "declarant_role_code": 1,
            "id_sistema": False,
            "taxpayer_code": self.env.company.l10n_it_codice_fiscale,
            "parent_company_vat_number": False,
            "company_code": "".join([char for char in self.env.company.vat if char.isdigit()]),
            "intermediary_code": self.env.company.account_representative_id.l10n_it_codice_fiscale if self.env.company.account_representative_id else False,
            "submission_commitment": 1,
            "commitment_date": fields.Date.today(),
            "subcontracting": False,
            "exceptional_events": False,
            "extraordinary_operations": False,
            "method": False,
        })

        if forced_options:
            options.update(forced_options)

        report_handler = self.env[self.report.custom_handler_model_name]
        return report_handler.export_tax_report_to_xml(options)['file_content']

    def test_all_settings_tags_in_xml(self):
        self.env.company.account_tax_periodicity = 'monthly'
        self.env.company.l10n_it_codice_fiscale = 12345670546
        # The following values can only be edited by inputting their value in the wizard.
        file_content = self._get_file_content(forced_options={
            "parent_company_vat_number": 12345678901,
            "intermediary_code": 12345678901,
            "id_sistema": 12345678901,
            "subcontracting": True,
            "exceptional_events": True,
            "extraordinary_operations": True,
            "method": 1,
        })
        decoded_file_content = file_content.decode()

        settings_tags = [
            "Intestazione",
            "CodiceFornitura",
            "CodiceFiscaleDichiarante",
            "CodiceCarica",
            "IdSistema",
            "Frontespizio",
            "CodiceFiscale",
            "AnnoImposta",
            "PartitaIVA",
            "PIVAControllante",
            "UltimoMese",
            "CFDichiarante",
            "CodiceCaricaDichiarante",
            "CodiceFiscaleSocieta",
            "FirmaDichiarazione",
            "CFIntermediario",
            "ImpegnoPresentazione",
            "DataImpegno",
            "FirmaIntermediario",
            "FlagConferma",
            "IdentificativoProdSoftware",
        ]

        for tag in settings_tags:
            self.assertIn(f"<iv:{tag}>", decoded_file_content, f"Tag <iv:{tag}> is missing in the XML export.")

    @freeze_time('2025-06-01')
    def test_xml_monthly_export(self):
        self._create_invoice_for_reported_period()
        self.env.company.account_tax_periodicity = 'monthly'
        file_content = self._get_file_content()
        decoded_file_content = file_content.decode()

        # If the file doesn't contain the three monthly groups, there is no need to test further
        for i, date in enumerate(date_utils.date_range(*date_utils.get_quarter(fields.Date.today()))):
            self.assertIn(f"<iv:NumeroModulo>{i + 1}</iv:NumeroModulo>", decoded_file_content)
            self.assertIn(f"<iv:Mese>{date.month}</iv:Mese>", decoded_file_content)

        expected_xml = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <iv:Fornitura xmlns:iv="urn:www.agenziaentrate.gov.it:specificheTecniche:sco:ivp" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <iv:Intestazione>
                    <iv:CodiceFornitura>IVP18</iv:CodiceFornitura>
                    <iv:CodiceCarica>1</iv:CodiceCarica>
                </iv:Intestazione>
                <iv:Comunicazione identificativo="00001">
                    <iv:Frontespizio>
                        <iv:AnnoImposta>2025</iv:AnnoImposta>
                        <iv:PartitaIVA>78926680725</iv:PartitaIVA>
                        <iv:UltimoMese>5</iv:UltimoMese>
                        <iv:CodiceCaricaDichiarante>1</iv:CodiceCaricaDichiarante>
                        <iv:CodiceFiscaleSocieta>78926680725</iv:CodiceFiscaleSocieta>
                        <iv:FirmaDichiarazione>1</iv:FirmaDichiarazione>
                        <iv:FlagConferma>1</iv:FlagConferma>
                        <iv:IdentificativoProdSoftware>ODOO S.A.</iv:IdentificativoProdSoftware>
                    </iv:Frontespizio>
                    <iv:DatiContabili>
                        <iv:Modulo>
                            <iv:NumeroModulo>1</iv:NumeroModulo>
                            <iv:Mese>4</iv:Mese>
                            <iv:TotaleOperazioniPassive>50,00</iv:TotaleOperazioniPassive>
                            <iv:IvaDetratta>2,00</iv:IvaDetratta>
                            <iv:IvaCredito>2,00</iv:IvaCredito>
                            <iv:ImportoACredito>2,00</iv:ImportoACredito>
                        </iv:Modulo>
                        <iv:Modulo>
                            <iv:NumeroModulo>2</iv:NumeroModulo>
                            <iv:Mese>5</iv:Mese>
                            <iv:TotaleOperazioniPassive>500,00</iv:TotaleOperazioniPassive>
                            <iv:IvaDetratta>20,00</iv:IvaDetratta>
                            <iv:IvaCredito>20,00</iv:IvaCredito>
                            <iv:ImportoACredito>20,00</iv:ImportoACredito>
                        </iv:Modulo>
                        <iv:Modulo>
                            <iv:NumeroModulo>3</iv:NumeroModulo>
                            <iv:Mese>6</iv:Mese>
                            <iv:TotaleOperazioniPassive>5000,00</iv:TotaleOperazioniPassive>
                            <iv:IvaDetratta>200,00</iv:IvaDetratta>
                            <iv:IvaCredito>200,00</iv:IvaCredito>
                            <iv:ImportoACredito>200,00</iv:ImportoACredito>
                        </iv:Modulo>
                    </iv:DatiContabili>
                </iv:Comunicazione>
            </iv:Fornitura>
        """

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(file_content),
            self.get_xml_tree_from_string(expected_xml),
        )

    @freeze_time('2025-06-01')
    def test_xml_quarterly_export(self):
        self._create_invoice_for_reported_period()
        self.env.company.account_tax_periodicity = 'trimester'
        file_content = self._get_file_content()
        decoded_file_content = file_content.decode()

        # If the file doesn't contain a single Trimester group, there is no need to test further
        self.assertIn("<iv:NumeroModulo>1</iv:NumeroModulo>", decoded_file_content)
        self.assertIn(f"<iv:Trimestre>{date_utils.get_quarter_number(fields.Date.today())}</iv:Trimestre>", decoded_file_content)

        expected_xml = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <iv:Fornitura xmlns:iv="urn:www.agenziaentrate.gov.it:specificheTecniche:sco:ivp" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <iv:Intestazione>
                    <iv:CodiceFornitura>IVP18</iv:CodiceFornitura>
                    <iv:CodiceCarica>1</iv:CodiceCarica>
                </iv:Intestazione>
                <iv:Comunicazione identificativo="00001">
                    <iv:Frontespizio>
                        <iv:AnnoImposta>2025</iv:AnnoImposta>
                        <iv:PartitaIVA>78926680725</iv:PartitaIVA>
                        <iv:UltimoMese>5</iv:UltimoMese>
                        <iv:CodiceCaricaDichiarante>1</iv:CodiceCaricaDichiarante>
                        <iv:CodiceFiscaleSocieta>78926680725</iv:CodiceFiscaleSocieta>
                        <iv:FirmaDichiarazione>1</iv:FirmaDichiarazione>
                        <iv:FlagConferma>1</iv:FlagConferma>
                        <iv:IdentificativoProdSoftware>ODOO S.A.</iv:IdentificativoProdSoftware>
                    </iv:Frontespizio>
                    <iv:DatiContabili>
                        <iv:Modulo>
                            <iv:NumeroModulo>1</iv:NumeroModulo>
                            <iv:Trimestre>2</iv:Trimestre>
                            <iv:TotaleOperazioniPassive>5550,00</iv:TotaleOperazioniPassive>
                            <iv:IvaDetratta>222,00</iv:IvaDetratta>
                            <iv:IvaCredito>222,00</iv:IvaCredito>
                            <iv:ImportoACredito>222,00</iv:ImportoACredito>
                        </iv:Modulo>
                    </iv:DatiContabili>
                </iv:Comunicazione>
            </iv:Fornitura>
        """

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(file_content),
            self.get_xml_tree_from_string(expected_xml),
        )
