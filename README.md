# [Multiple-type-fields-on-Card-for-Anki-2.1]()
A port of the Anki 2.0 Addon ["Multiple type fields on Card"](https://ankiweb.net/shared/info/689574440). All credit goes to the author of that package. 

This addon allows the user to specify multiple independent `{{type:}}` fields on one card.  

Example screenshot: ![Example screenshot](/multiple_type_fields_on_card_for_2_1_example.png)

Template for the screenshot:

For the Front (not shown in the screenshot):

    {{infinitive}}

    <br>;
    <br>;

    simple past: {{type:simple past}}

    <br>;

    past participle: {{type:past participle}}

For the Back (shown in the screenshot):

    {{FrontSide}} 

This Addon is probably incompatible with a lot of other Addons, as it still Monkey-Patches a few functions directly instead of using hooks. If anyone wants to help improve the code or found a bug or incompatibility, please comment on the Addon page or create an Issue here on Github.
