module(...,package.seeall)

-- Configuration
local scale = 65536  -- 2^16sp = 1pt
local output_file = "glyph_map.json"

-- Node type constants
local HLIST = node.id("hlist")
local VLIST = node.id("vlist")
local GLYPH = node.id("glyph")

-- Global data structure to store mappings
local glyph_data = {}
local glyph_counter = 0

-- Write current position to be called via late_lua
local function capture_position()
    -- Get current position from TeX's internal registers
    -- In DVI mode, we track the current point more directly
    local current_h = tex.getdimen("dimen0") -- horizontal position
    local current_v = tex.getdimen("dimen1") -- vertical position
    
    -- Alternative method: use node position if available
    if status.get_node_position then
        current_h, current_v = status.get_node_position()
    end
    
    -- Store position for the most recent glyph (in DVI coordinates)
    if glyph_counter > 0 then
        glyph_data[glyph_counter].dvi_h = current_h / scale
        glyph_data[glyph_counter].dvi_v = current_v / scale
    end
end

-- Transform DVI coordinates to SVG coordinates
local function dvi_to_svg(dvi_x, dvi_y, page_height)
    -- DVI uses bottom-left origin like PDF
    -- dvisvgm typically uses 1pt = 1 SVG unit
    -- SVG uses top-left origin, so we need to flip Y
    return dvi_x, page_height - dvi_y
end

-- Extract font information
local function get_font_info(glyph_node)
    local font_id = glyph_node.font
    local font_info = font.getfont(font_id)
    return {
        name = font_info.fullname or font_info.name,
        size = font_info.size / scale,
        id = font_id
    }
end

-- Process nodes recursively
local function process_nodes(head, parent, current_h, current_v)
    current_h = current_h or 0
    current_v = current_v or 0
    
    while head do
        if head.id == GLYPH then
            glyph_counter = glyph_counter + 1
            
            -- Store glyph information with current position
            glyph_data[glyph_counter] = {
                char = head.char,
                unicode = string.format("U+%04X", head.char),
                utf8 = string.utfcharacter(head.char),
                width = head.width / scale,
                height = head.height / scale,
                depth = head.depth / scale,
                font = get_font_info(head),
                sequence_id = glyph_counter,
                dvi_h = current_h / scale,
                dvi_v = current_v / scale
            }
            
            -- Advance horizontal position
            current_h = current_h + head.width
            
        elseif head.id == HLIST then
            -- Process horizontal list
            process_nodes(head.list, head, current_h, current_v)
            current_h = current_h + head.width
            
        elseif head.id == VLIST then
            -- Process vertical list  
            process_nodes(head.list, head, current_h, current_v + head.height)
            current_v = current_v + head.height + head.depth
        end
        
        head = head.next
    end
end

-- Main shipout function
function shipout()
    -- Reset data
    glyph_data = {}
    glyph_counter = 0
    
    -- Get shipout box and process
    local shipout_box = tex.getbox("ShipoutBox")
    local page_height = shipout_box.height / scale
    
    -- Process all nodes with position tracking
    process_nodes(shipout_box.list, shipout_box, 0, 0)
    
    -- Transform coordinates and prepare output
    local output_data = {
        page_dimensions = {
            width = shipout_box.width / scale,
            height = page_height
        },
        glyphs = {}
    }
    
    for i, glyph in pairs(glyph_data) do
        if glyph.dvi_h and glyph.dvi_v then
            local svg_x, svg_y = dvi_to_svg(glyph.dvi_h, glyph.dvi_v, page_height)
            
            table.insert(output_data.glyphs, {
                sequence_id = glyph.sequence_id,
                character = glyph.utf8,
                unicode = glyph.unicode,
                position = {
                    dvi = {h = glyph.dvi_h, v = glyph.dvi_v},
                    svg = {x = svg_x, y = svg_y}
                },
                dimensions = {
                    width = glyph.width,
                    height = glyph.height,
                    depth = glyph.depth
                },
                font = glyph.font
            })
        end
    end
    
    -- Write JSON output
    local json_output = serialize_json(output_data)
    local file = io.open(output_file, "w")
    file:write(json_output)
    file:close()
end

-- Simple JSON serializer
function serialize_json(obj, indent)
    indent = indent or 0
    local spacing = string.rep("  ", indent)
    
    if type(obj) == "table" then
        local is_array = #obj > 0
        local items = {}
        local iter = is_array and ipairs or pairs

        for k, v in iter(obj) do
            local val = serialize_json(v, indent + 1)
            table.insert(items, is_array and val or ('"' .. tostring(k) .. '": ' .. val))
        end

        local open, close = is_array and "[\n" or "{\n", is_array and "\n" .. spacing .. "]" or "\n" .. spacing .. "}"
        return open .. next_spacing .. table.concat(items, ",\n" .. next_spacing) .. close
    elseif type(obj) == "string" then
        return '"' .. obj:gsub('"', '\\"') .. '"'
    elseif type(obj) == "number" then
        return tostring(obj)
    elseif type(obj) == "boolean" then
        return tostring(obj)
    else
        error("Unsupported type: " .. type(obj))
    end
end